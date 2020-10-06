import datetime
from collections import defaultdict

from gtimelog.core.time import TimeCollection
from gtimelog.core.utils import format_duration_short, format_duration_long, report_categories, get_mtime


class Reports(object):
    """Generation of reports."""

    def __init__(self, window, email_headers=True, style='plain'):
        self.window = window
        self.email_headers = email_headers
        self.style = style

    def _categorizing_report(self, output, email, subject, period_name):
        """A report that displays entries by category.

        Writes a report template in RFC-822 format to output.

        The report looks like
        |                             time
        | Overhead:
        |   Status meeting              43
        |   Mail                      1:50
        | --------------------------------
        |                             2:33
        |
        | Compass:
        |   Compass: hotpatch         2:13
        |   Call with a client          30
        | --------------------------------
        |                             3:43
        |
        | No category:
        |   SAT roundup               1:00
        | --------------------------------
        |                             1:00
        |
        | Total work done this week: 6:26
        |
        | Categories by time spent:
        |
        | Compass       3:43
        | Overhead      2:33
        | No category   1:00

        """
        window = self.window

        if self.email_headers:
            output.write("To: %(email)s\n" % {'email': email})
            output.write("Subject: %s\n" % subject)
            output.write('\n')

        items = list(window.all_entries())
        if not items:
            output.write("No work done this %s.\n" % period_name)
            return
        output.write(" " * 46)
        output.write("                   time\n")

        total_work, total_slacking = window.totals()
        entries, totals = window.categorized_work_entries()
        if entries:
            if None in entries:
                e = entries.pop(None)
                categories = sorted(entries)
                categories.append('No category')
                entries['No category'] = e
                t = totals.pop(None)
                totals['No category'] = t
            else:
                categories = sorted(entries)
            for cat in categories:
                output.write('%s:\n' % cat)

                work = [(entry, duration)
                        for start, entry, duration in entries[cat]]
                work.sort()
                for entry, duration in work:
                    if not duration:
                        continue  # skip empty "arrival" entries

                    entry = entry[:1].upper() + entry[1:]
                    output.write(u"  %-61s  %+5s\n" %
                                 (entry, format_duration_short(duration)))

                output.write('-' * 70 + '\n')
                output.write(u"%+70s\n" % format_duration_short(totals[cat]))
                output.write('\n')
        output.write("Total work done this %s: %s\n" %
                     (period_name, format_duration_short(total_work)))

        output.write('\n')

        ordered_by_time = [(time, cat) for cat, time in totals.items()]
        ordered_by_time.sort(reverse=True)
        max_cat_length = max([len(cat) for cat in totals.keys()])
        line_format = '  %-' + str(max_cat_length + 4) + 's %+5s\n'
        output.write('Categories by time spent:\n')
        for time, cat in ordered_by_time:
            output.write(line_format % (cat, format_duration_short(time)))

        tags = self.window.set_of_all_tags()
        if tags:
            self._report_tags(output, tags)

    def _report_tags(self, output, tags):
        """Helper method that lists time spent per tag.

        Use this to add a section in a report looks similar to this:

        sysadmin:     2 hours 1 min
        www:          18 hours 45 min
        mailserver:   3 hours

        Note that duration may not add up to the total working time,
        as a single entry can have multiple or no tags at all!

        Argument `tags` is a set of tags (string).  It is not modified.
        """
        output.write('\n')
        output.write('Time spent in each area:\n')
        output.write('\n')
        # sum work and slacking time per tag; we do not care in this report
        tags_totals = {}
        for tag in tags:
            spent_working, spent_slacking = self.window.totals(tag)
            tags_totals[tag] = spent_working + spent_slacking
        # compute width of tag label column
        max_tag_length = max([len(tag) for tag in tags_totals.keys()])
        line_format = '  %-' + str(max_tag_length + 4) + 's %+5s\n'
        # sort by time spent (descending)
        for tag, spent in sorted(tags_totals.items(),
                                 key=(lambda it: it[1]),
                                 reverse=True):
            output.write(line_format % (tag, format_duration_short(spent)))
        output.write('\n')
        output.write(
            'Note that area totals may not add up to the period totals,\n'
            'as each entry may be belong to multiple areas (or none at all).\n')

    def _plain_report(self, output, email, subject, period_name):
        """Format a report that does not categorize entries.

        Writes a report template in RFC-822 format to output.
        """
        window = self.window

        if self.email_headers:
            output.write("To: %(email)s\n" % {'email': email})
            output.write('Subject: %s\n' % subject)
            output.write('\n')

        items = list(window.all_entries())
        if not items:
            output.write("No work done this %s.\n" % period_name)
            return
        output.write(" " * 46)
        output.write("                time\n")
        work, slack = window.grouped_entries()
        total_work, total_slacking = window.totals()
        categories = {}
        if work:
            work = [(entry, duration) for start, entry, duration in work]
            work.sort()
            for entry, duration in work:
                if not duration:
                    continue  # skip empty "arrival" entries

                cat, task = TimeCollection.split_category(entry)
                categories[cat] = categories.get(
                    cat, datetime.timedelta(0)) + duration

                entry = entry[:1].upper() + entry[1:]
                output.write(u"%-62s  %s\n" %
                             (entry, format_duration_long(duration)))
            output.write('\n')
        output.write("Total work done this %s: %s\n" %
                     (period_name, format_duration_long(total_work)))

        if categories:
            report_categories(output, categories)

        tags = self.window.set_of_all_tags()
        if tags:
            self._report_tags(output, tags)

    def weekly_report_subject(self, who):
        week = self.window.min_timestamp.isocalendar()[1]
        return u'Weekly report for %s (week %02d)' % (who, week)

    def weekly_report(self, output, email, who):
        if self.style == 'categorized':
            return self.weekly_report_categorized(output, email, who)
        else:
            return self.weekly_report_plain(output, email, who)

    def weekly_report_plain(self, output, email, who):
        """Format a weekly report."""
        subject = self.weekly_report_subject(who)
        return self._plain_report(output, email, subject, period_name='week')

    def weekly_report_categorized(self, output, email, who):
        """Format a weekly report with entries displayed  under categories."""
        subject = self.weekly_report_subject(who)
        return self._categorizing_report(output, email, subject, period_name='week')

    def monthly_report_subject(self, who):
        month = self.window.min_timestamp.strftime('%Y/%m')
        return u'Monthly report for %s (%s)' % (who, month)

    def monthly_report(self, output, email, who):
        if self.style == 'categorized':
            return self.monthly_report_categorized(output, email, who)
        else:
            return self.monthly_report_plain(output, email, who)

    def monthly_report_plain(self, output, email, who):
        """Format a monthly report ."""
        subject = self.monthly_report_subject(who)
        return self._plain_report(output, email, subject, period_name='month')

    def monthly_report_categorized(self, output, email, who):
        """Format a monthly report with entries displayed  under categories."""
        subject = self.monthly_report_subject(who)
        return self._categorizing_report(output, email, subject, period_name='month')

    def custom_range_report_subject(self, who):
        minimum = self.window.min_timestamp.strftime('%Y-%m-%d')
        maximum = (self.window.max_timestamp - datetime.timedelta(1)).strftime('%Y-%m-%d')
        return u'Custom date range report for %s (%s - %s)' % (who, minimum, maximum)

    def custom_range_report_categorized(self, output, email, who):
        """Format a custom range report with entries displayed under categories."""
        subject = self.custom_range_report_subject(who)
        return self._categorizing_report(output, email, subject, period_name='custom range')

    def daily_report_subject(self, who):
        # strftime('%a') would give us translated names, but we want our
        # reports to be standardized and machine-parseable
        weekday_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        weekday = weekday_names[self.window.min_timestamp.weekday()]
        week = self.window.min_timestamp.isocalendar()[1]
        return (u"{0:%Y-%m-%d} report for {who}"
                u" ({weekday}, week {week:0>2})".format(self.window.min_timestamp,
                                                        who=who,
                                                        weekday=weekday,
                                                        week=week))

    def daily_report(self, output, email, who):
        """Format a daily report.

        Writes a daily report template in RFC-822 format to output.
        """
        window = self.window
        if self.email_headers:
            output.write(u"To: %s\n" % email)
            output.write(u"Subject: %s\n" % self.daily_report_subject(who))
            output.write('\n')
        items = list(window.all_entries())
        if not items:
            output.write("No work done today.\n")
            return
        start, stop, duration, tags, entry = items[0]
        entry = entry[:1].upper() + entry[1:]
        output.write("%s at %s\n" % (entry, start.strftime('%H:%M')))
        output.write('\n')
        work, slack = window.grouped_entries()
        total_work, total_slacking = window.totals()
        categories = {}
        if work:
            for start, entry, duration in work:
                entry = entry[:1].upper() + entry[1:]
                output.write(u"%-62s  %s\n" % (entry,
                                               format_duration_long(duration)))
                cat, task = TimeCollection.split_category(entry)
                categories[cat] = categories.get(
                    cat, datetime.timedelta(0)) + duration

            output.write('\n')
        output.write("Total work done: %s\n" % format_duration_long(total_work))

        if categories:
            report_categories(output, categories)

        output.write('Slacking:\n\n')

        if slack:
            for start, entry, duration in slack:
                entry = entry[:1].upper() + entry[1:]
                output.write(u"%-62s  %s\n" % (entry,
                                               format_duration_long(duration)))
            output.write('\n')
        output.write("Time spent slacking: %s\n" %
                     format_duration_long(total_slacking))

        tags = self.window.set_of_all_tags()
        if tags:
            self._report_tags(output, tags)


class ReportRecord(object):
    """A record of sent reports."""

    # Let's be compatible with https://github.com/ProgrammersOfVilnius/gtimesheet
    DAILY = 'daily'
    WEEKLY = 'weekly'
    MONTHLY = 'monthly'

    def __init__(self, filename):
        self.filename = filename
        self.last_mtime = None
        self._records = defaultdict(list)

    @classmethod
    def get_report_id(cls, report_kind, date):
        if report_kind == cls.DAILY:
            return date.strftime('%Y-%m-%d')
        elif report_kind == cls.WEEKLY:
            # I'd prefer the ISO 8601 format (2015-W31 instead of 2015/31), but
            # let's be compatible with https://github.com/ProgrammersOfVilnius/gtimesheet
            return '{}/{}'.format(*date.isocalendar()[:2])
        elif report_kind == cls.MONTHLY:
            return date.strftime('%Y-%m')
        else:  # pragma: nocover
            raise AssertionError('Bug: unexpected report kind: %r' % report_kind)

    def record(self, report_kind, report_date, recipient, now=None):
        """Record that a record has been sent.

        report_kind is one of DAILY, WEEKLY, MONTHLY.

        report_date is a date in the report period.

        recipient is an email address.  The intent here is to distinguish
        real reports sent to activity@yourcompany.example.com from test
        reports sent to a test address.
        """
        assert report_kind in (self.DAILY, self.WEEKLY, self.MONTHLY)
        assert isinstance(report_date, datetime.date)
        if now is None:
            now = datetime.datetime.now()
        timestamp = now.strftime('%Y-%m-%d %H:%M:%S')
        report_id = self.get_report_id(report_kind, report_date)
        with open(self.filename, 'a') as f:
            f.write("{},{},{},{}\n".format(timestamp, report_kind, report_id, recipient))
        if self.last_mtime is not None:
            self.last_mtime = get_mtime(self.filename)
            self._records[report_kind, report_id].append(recipient)

    def check_reload(self):
        mtime = get_mtime(self.filename)
        if mtime != self.last_mtime:
            self.reread()

    def reread(self):
        self.last_mtime = get_mtime(self.filename)
        self._records.clear()
        try:
            with open(self.filename) as f:
                for line in f:
                    try:
                        timestamp, report_kind, report_id, recipient = line.split(',', 3)
                    except ValueError:
                        continue
                    self._records[report_kind, report_id].append(recipient.strip())
        except IOError:
            pass

    def get_recipients(self, report_kind, report_date):
        """Look up who received a particular report.

        report_kind is one of DAILY, WEEKLY, MONTHLY.

        report_date is a date in the report period.

        Returns a list of recipients, in order.
        """
        self.check_reload()
        report_id = self.get_report_id(report_kind, report_date)
        return self._records.get((report_kind, report_id), [])
