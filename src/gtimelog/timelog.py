"""
Non-GUI bits of gtimelog.
"""

from __future__ import unicode_literals

import codecs
import collections
import csv
import datetime
import os
import socket
import sys
import re
import urllib
from hashlib import md5
from operator import itemgetter


PY3 = sys.version_info[0] >= 3


def as_minutes(duration):
    """Convert a datetime.timedelta to an integer number of minutes."""
    return duration.days * 24 * 60 + duration.seconds // 60


def as_hours(duration):
    """Convert a datetime.timedelta to a float number of hours."""
    return duration.days * 24.0 + duration.seconds / (60.0 * 60.0)


def format_duration(duration):
    """Format a datetime.timedelta with minute precision."""
    h, m = divmod(as_minutes(duration), 60)
    return '%d h %d min' % (h, m)


def format_duration_short(duration):
    """Format a datetime.timedelta with minute precision."""
    h, m = divmod((duration.days * 24 * 60 + duration.seconds // 60), 60)
    return '%d:%02d' % (h, m)


def format_duration_long(duration):
    """Format a datetime.timedelta with minute precision, long format."""
    h, m = divmod((duration.days * 24 * 60 + duration.seconds // 60), 60)
    if h and m:
        return '%d hour%s %d min' % (h, h != 1 and "s" or "", m)
    elif h:
        return '%d hour%s' % (h, h != 1 and "s" or "")
    else:
        return '%d min' % m


def parse_datetime(dt):
    """Parse a datetime instance from 'YYYY-MM-DD HH:MM' formatted string."""
    if len(dt) != 16 or dt[4] != '-' or dt[7] != '-' or dt[10] != ' ' or dt[13] != ':':
        raise ValueError('bad date time: ', dt)
    try:
        year = int(dt[:4])
        month = int(dt[5:7])
        day = int(dt[8:10])
        hour = int(dt[11:13])
        min = int(dt[14:])
    except ValueError:
        raise ValueError('bad date time: ', dt)
    return datetime.datetime(year, month, day, hour, min)


def parse_time(t):
    """Parse a time instance from 'HH:MM' formatted string."""
    m = re.match(r'^(\d+):(\d+)$', t)
    if not m:
        raise ValueError('bad time: ', t)
    hour, min = map(int, m.groups())
    return datetime.time(hour, min)


def virtual_day(dt, virtual_midnight):
    """Return the "virtual day" of a timestamp.

    Timestamps between midnight and "virtual midnight" (e.g. 2 am) are
    assigned to the previous "virtual day".
    """
    if dt.time() < virtual_midnight:     # assign to previous day
        return dt.date() - datetime.timedelta(1)
    return dt.date()


def different_days(dt1, dt2, virtual_midnight):
    """Check whether dt1 and dt2 are on different "virtual days".

    See virtual_day().
    """
    return virtual_day(dt1, virtual_midnight) != virtual_day(dt2,
                                                             virtual_midnight)


def first_of_month(date):
    """Return the first day of the month for a given date."""
    return date.replace(day=1)


def prev_month(date):
    """Return the first day of the previous month."""
    if date.month == 1:
        return datetime.date(date.year - 1, 12, 1)
    else:
        return datetime.date(date.year, date.month - 1, 1)


def next_month(date):
    """Return the first day of the next month."""
    if date.month == 12:
        return datetime.date(date.year + 1, 1, 1)
    else:
        return datetime.date(date.year, date.month + 1, 1)


def uniq(l):
    """Return list with consecutive duplicates removed."""
    result = l[:1]
    for item in l[1:]:
        if item != result[-1]:
            result.append(item)
    return result


Entry = collections.namedtuple('Entry', 'start stop duration tags entry')


class TimeCollection(object):
    """A collection of timestamped events.

    self.items is a list of (timestamp, event_title) tuples.

    Time intervals between events within the time window form entries that have
    a start time, a stop time, and a duration.  Entry title is the title of the
    event that occurred at the stop time.

    The first event of each day also creates a special "start" entry of zero
    duration.

    Entries that span virtual midnight boundaries are also converted to
    "start" entries at their end point.
    """

    def __init__(self, virtual_midnight):
        self.items = []
        self.virtual_midnight = virtual_midnight

    def __repr__(self):
        return '<TimeCollection ({} items)>'.format(len(self.items))

    def first_time(self):
        """Return the time of the first entry.

        Returns a datetime.datetime instance or None, if the window is empty.
        """
        if not self.items:
            return None
        return self.items[0][0]

    def last_time(self):
        """Return the time of the last entry.

        Returns a datetime.datetime instance or None, if the window is empty.
        """
        if not self.items:
            return None
        return self.items[-1][0]

    def last_entry(self):
        """Return the last entry (or None if there are no events).

        It is always true that

            self.last_entry() == list(self.all_entries())[-1]

        if self.items it not empty.
        """
        if not self.items:
            return None
        stop = self.items[-1][0]
        entry = self.items[-1][1]
        if len(self.items) == 1:
            start = stop
        else:
            start = self.items[-2][0]
        if different_days(start, stop, self.virtual_midnight):
            start = stop
        duration = stop - start
        entry, tags = self._split_entry_and_tags(entry)
        return Entry(start, stop, duration, tags, entry)

    def all_entries(self):
        """Iterate over all entries.

        Yields Entry tuples.  The first entry in each day has a duration
        of 0.
        """
        stop = None
        for item in self.items:
            start = stop
            stop = item[0]
            entry = item[1]
            if start is None or different_days(start, stop,
                                               self.virtual_midnight):
                start = stop
            duration = stop - start
            entry, tags = self._split_entry_and_tags(entry)
            yield Entry(start, stop, duration, tags, entry)

    @staticmethod
    def _split_entry_and_tags(entry):
        """
        Split the entry title (proper) from the trailing tags.

        Tags are separated from the title by a `` -- `` marker:
        anything *before* the marker is the entry title,
        anything *following* it is the (space-separated) set of tags.

        Return a tuple consisting of entry title and set of tags.
        """
        if ' -- ' in entry:
            entry, tags_bundle = entry.split(' -- ', 1)
            # there might be spaces preceding ' -- '
            entry = entry.rstrip()
            tags = set(tags_bundle.split())
            # put back '**' and '***' if they were in the tags part
            if '***' in tags:
                entry += ' ***'
                tags.remove('***')
            elif '**' in tags:
                entry += ' **'
                tags.remove('**')
        else:
            tags = set()
        return entry, tags

    def set_of_all_tags(self):
        """Return the set of all tags mentioned in entries."""
        all_tags = set()
        for entry in self.all_entries():
            all_tags.update(entry.tags)
        return all_tags

    def count_days(self):
        """Count days that have entries."""
        count = 0
        last = None
        for entry in self.all_entries():
            if last is None or different_days(last, entry.start,
                                              self.virtual_midnight):
                last = entry.start
                count += 1
        return count

    def grouped_entries(self, skip_first=True):
        """Return consolidated entries (grouped by entry title).

        Returns two lists: work entries and slacking entries.  Slacking
        entries are identified by finding two asterisks in the title.
        Entry lists are sorted, and contain (start, entry, duration) tuples.
        """
        work = {}
        slack = {}
        for start, stop, duration, tags, entry in self.all_entries():
            if skip_first:
                # XXX: in case of for multi-day windows, this should skip
                # the 1st entry of each day
                skip_first = False
                continue
            if '***' in entry:
                continue
            if '**' in entry:
                entries = slack
            else:
                entries = work
            if entry in entries:
                old_start, old_entry, old_duration = entries[entry]
                start = min(start, old_start)
                duration += old_duration
            entries[entry] = (start, entry, duration)
        work = sorted(work.values())
        slack = sorted(slack.values())
        return work, slack

    def categorized_work_entries(self, skip_first=True):
        """Return consolidated work entries grouped by category.

        Category is a string preceding the first ':' in the entry.

        Return two dicts:
          - {<category>: <entry list>}, where <category> is a category string
            and <entry list> is a sorted list that contains tuples (start,
            entry, duration); entry is stripped of its category prefix.
          - {<category>: <total duration>}, where <total duration> is the
            total duration of work in the <category>.
        """

        work, slack = self.grouped_entries(skip_first=skip_first)
        entries = {}
        totals = {}
        for start, entry, duration in work:
            if ': ' in entry:
                cat, clipped_entry = entry.split(': ', 1)
                entry_list = entries.get(cat, [])
                entry_list.append((start, clipped_entry, duration))
                entries[cat] = entry_list
                totals[cat] = totals.get(cat, datetime.timedelta(0)) + duration
            else:
                entry_list = entries.get(None, [])
                entry_list.append((start, entry, duration))
                entries[None] = entry_list
                totals[None] = totals.get(
                    None, datetime.timedelta(0)) + duration
        return entries, totals

    def totals(self, tag=None):
        """Calculate total time of work and slacking entries.

        If optional argument `tag` is given, only compute
        totals for entries marked with the given tag.

        Returns (total_work, total_slacking) tuple.

        Slacking entries are identified by finding two asterisks in the title.

        Assuming that

            total_work, total_slacking = self.totals()
            work, slacking = self.grouped_entries()

        It is always true that

            total_work = sum([duration for start, entry, duration in work])
            total_slacking = sum([duration
                                  for start, entry, duration in slacking])

        (that is, it would be true if sum could operate on timedeltas).
        """
        total_work = total_slacking = datetime.timedelta(0)
        for start, stop, duration, tags, entry in self.all_entries():
            if tag is not None and tag not in tags:
                continue
            if '**' in entry:
                total_slacking += duration
            else:
                total_work += duration
        return total_work, total_slacking


class TimeWindow(TimeCollection):
    """A window into a time log.

    Includes all events that took place between min_timestamp and
    max_timestamp.  Includes events that took place at min_timestamp, but
    excludes events that took place at max_timestamp.
    """

    def __init__(self, original, min_timestamp, max_timestamp):
        super(TimeWindow, self).__init__(original.virtual_midnight)
        self.min_timestamp = min_timestamp
        self.max_timestamp = max_timestamp
        self.items = [item for item in original.items
                      if min_timestamp <= item[0] < max_timestamp]

    def __repr__(self):
        return '<TimeWindow: {}..{}>'.format(self.min_timestamp,
                                             self.max_timestamp)


class Exports(object):
    """Exporting of events."""

    def __init__(self, window):
        self.window = window

    def icalendar(self, output):
        """Create an iCalendar file with activities."""
        output.write("BEGIN:VCALENDAR\n")
        output.write("PRODID:-//gtimelog.org/NONSGML GTimeLog//EN\n")
        output.write("VERSION:2.0\n")
        idhost = socket.getfqdn()
        dtstamp = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        def _hash(start, stop, entry):
            return md5(("%s%s%s" % (start, stop, entry)).encode('UTF-8')).hexdigest()
        for start, stop, duration, tags, entry in self.window.all_entries():
            output.write("BEGIN:VEVENT\n")
            output.write("UID:%s@%s\n" % (_hash(start, stop, entry), idhost))
            output.write("SUMMARY:%s\n" % (entry.replace('\\', '\\\\'))
                                                .replace(';', '\\;')
                                                .replace(',', '\\,'))
            output.write("DTSTART:%s\n" % start.strftime('%Y%m%dT%H%M%S'))
            output.write("DTEND:%s\n" % stop.strftime('%Y%m%dT%H%M%S'))
            output.write("DTSTAMP:%s\n" % dtstamp)
            output.write("END:VEVENT\n")
        output.write("END:VCALENDAR\n")

    def to_csv_complete(self, output, title_row=True):
        """Export work entries to a CSV file.

        The file has two columns: task title and time (in minutes).
        """
        writer = CSVWriter(output)
        if title_row:
            writer.writerow(["task", "time (minutes)"])
        work, slack = self.window.grouped_entries()
        work = [(entry, as_minutes(duration))
                for start, entry, duration in work
                if duration] # skip empty "arrival" entries
        work.sort()
        writer.writerows(work)

    def to_csv_daily(self, output, title_row=True):
        """Export daily work, slacking, and arrival times to a CSV file.

        The file has four columns: date, time from midnight til arrival at
        work, slacking, and work (in decimal hours).
        """
        writer = CSVWriter(output)
        if title_row:
            writer.writerow(["date", "day-start (hours)",
                             "slacking (hours)", "work (hours)"])

        # sum timedeltas per date
        # timelog must be cronological for this to be dependable

        d0 = datetime.timedelta(0)
        days = {} # date -> [time_started, slacking, work]
        dmin = None
        for start, stop, duration, tags, entry in self.window.all_entries():
            if dmin is None:
                dmin = start.date()
            day = days.setdefault(start.date(),
                                  [datetime.timedelta(minutes=start.minute,
                                                      hours=start.hour),
                                   d0, d0])
            if '**' in entry:
                day[1] += duration
            else:
                day[2] += duration

        if dmin:
            # fill in missing dates - aka. weekends
            dmax = start.date()
            while dmin <= dmax:
                days.setdefault(dmin, [d0, d0, d0])
                dmin += datetime.timedelta(days=1)

        # convert to hours, and a sortable list
        items = sorted(
            (day, as_hours(start), as_hours(slacking), as_hours(work))
            for day, (start, slacking, work) in days.items())
        writer.writerows(items)


class Reports(object):
    """Generation of reports."""

    def __init__(self, window):
        self.window = window

    def _categorizing_report(self, output, email, who, subject, period_name):
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
                        continue # skip empty "arrival" entries

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

    def _report_categories(self, output, categories):
        """A helper method that lists time spent per category.

        Use this to add a section in a report looks similar to this:

        Administration:  2 hours 1 min
        Coding:          18 hours 45 min
        Learning:        3 hours

        category is a dict of entries (<category name>: <duration>).
        It is not preserved.
        """
        output.write('\n')
        output.write("By category:\n")
        output.write('\n')

        no_cat = categories.pop(None, None)
        items = sorted(categories.items())
        if no_cat is not None:
            items.append(('(none)', no_cat))
        for cat, duration in items:
            output.write(u"%-62s  %s\n" % (
                cat, format_duration_long(duration)))
        output.write('\n')

    def _plain_report(self, output, email, who, subject, period_name):
        """Format a report that does not categorize entries.

        Writes a report template in RFC-822 format to output.
        """
        window = self.window

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
                    continue # skip empty "arrival" entries

                if ': ' in entry:
                    cat, task = entry.split(': ', 1)
                    categories[cat] = categories.get(
                        cat, datetime.timedelta(0)) + duration
                else:
                    categories[None] = categories.get(
                        None, datetime.timedelta(0)) + duration

                entry = entry[:1].upper() + entry[1:]
                output.write(u"%-62s  %s\n" %
                             (entry, format_duration_long(duration)))
            output.write('\n')
        output.write("Total work done this %s: %s\n" %
                     (period_name, format_duration_long(total_work)))

        if categories:
            self._report_categories(output, categories)

        tags = self.window.set_of_all_tags()
        if tags:
            self._report_tags(output, tags)

    def weekly_report_categorized(self, output, email, who):
        """Format a weekly report with entries displayed  under categories."""
        week = self.window.min_timestamp.isocalendar()[1]
        subject = u'Weekly report for %s (week %02d)' % (who, week)
        return self._categorizing_report(output, email, who, subject,
                                         period_name='week')

    def monthly_report_categorized(self, output, email, who):
        """Format a monthly report with entries displayed  under categories."""
        month = self.window.min_timestamp.strftime('%Y/%m')
        subject = u'Monthly report for %s (%s)' % (who, month)
        return self._categorizing_report(output, email, who, subject,
                                         period_name='month')

    def weekly_report_plain(self, output, email, who):
        """Format a weekly report ."""
        week = self.window.min_timestamp.isocalendar()[1]
        subject = u'Weekly report for %s (week %02d)' % (who, week)
        return self._plain_report(output, email, who, subject,
                                  period_name='week')

    def monthly_report_plain(self, output, email, who):
        """Format a monthly report ."""
        month = self.window.min_timestamp.strftime('%Y/%m')
        subject = u'Monthly report for %s (%s)' % (who, month)
        return self._plain_report(output, email, who, subject,
                                  period_name='month')

    def custom_range_report_categorized(self, output, email, who):
        """Format a custom range report with entries displayed  under categories."""
        min = self.window.min_timestamp.strftime('%Y-%m-%d')
        max = self.window.max_timestamp - datetime.timedelta(1)
        max = max.strftime('%Y-%m-%d')
        subject = u'Custom date range report for %s (%s - %s)' % (who, min, max)
        return self._categorizing_report(output, email, who, subject,
                                         period_name='custom range')

    def daily_report(self, output, email, who):
        """Format a daily report.

        Writes a daily report template in RFC-822 format to output.
        """
        window = self.window

        # Locale is set as a side effect of 'import gtk', so strftime('%a')
        # would give us translated names
        weekday_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        weekday = weekday_names[window.min_timestamp.weekday()]
        week = window.min_timestamp.isocalendar()[1]
        output.write(u"To: %s\n" % email)
        output.write(u"Subject: {0:%Y-%m-%d} report for {who}"
                     u" ({weekday}, week {week:0>2})\n".format(
                         window.min_timestamp, who=who,
                         weekday=weekday, week=week))
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
                if ': ' in entry:
                    cat, task = entry.split(': ', 1)
                    categories[cat] = categories.get(
                        cat, datetime.timedelta(0)) + duration
                else:
                    categories[None] = categories.get(
                        None, datetime.timedelta(0)) + duration

            output.write('\n')
        output.write("Total work done: %s\n" % format_duration_long(total_work))

        if categories:
            self._report_categories(output, categories)

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


class TimeLog(TimeCollection):
    """Time log.

    A time log contains a time window for today, and can add new entries at
    the end.
    """

    def __init__(self, filename, virtual_midnight):
        super(TimeLog, self).__init__(virtual_midnight)
        self.filename = filename
        self.reread()

    def virtual_today(self):
        """Return today's date, adjusted for virtual midnight."""
        return virtual_day(datetime.datetime.now(), self.virtual_midnight)

    def check_reload(self):
        """Look at the mtime of timelog.txt, and reload it if necessary.

        Returns True if the file was reloaded.
        """
        mtime = self.get_mtime()
        if mtime != self.last_mtime:
            self.reread()
            return True
        else:
            return False

    def get_mtime(self):
        """Return the mtime of self.filename, if it exists.

        Returns None if the file doesn't exist.
        """
        # Accept any file-like object instead of a filename (for the benefit of
        # unit tests).
        if hasattr(self.filename, 'read'):
            return None
        try:
            return os.stat(self.filename).st_mtime
        except OSError:
            return None

    def reread(self):
        """Reload the log file."""
        self.day = self.virtual_today()
        self.last_mtime = self.get_mtime()
        try:
            if hasattr(self.filename, 'read'):
                # accept any file-like object
                # this is a hook for unit tests, really
                self.filename.seek(0)
                self.items = self._read(self.filename)
            else:
                with open(self.filename, 'rb') as f:
                    data = f.read()
                self.items = self._read(data.decode('UTF-8').splitlines())
        except IOError:
            self.items = []
        self.window = self.window_for_day(self.day)

    def _read(self, f):
        items = []
        for line in f:
            time, sep, entry = line.partition(': ')
            if not sep:
                continue
            try:
                time = parse_datetime(time)
            except ValueError:
                continue
            entry = entry.strip()
            items.append((time, entry))
        # There's code that relies on entries being sorted.  The entries really
        # should be already sorted in the file, but sometimes the user edits
        # timelog.txt directly and introduces errors.
        # XXX: instead of quietly resorting them we should inform the user if
        # there are errors
        # Note that we must preserve the relative order of entries with
        # the same timestamp: https://bugs.launchpad.net/gtimelog/+bug/708825
        items.sort(key=itemgetter(0))
        return items

    def window_for(self, min, max):
        """Return a TimeWindow for a specified time interval.

        ``min`` and ``max`` should be datetime.datetime instances.  The
        interval is half-open (inclusive at ``min``, exclusive at ``max``).
        """
        return TimeWindow(self, min, max)

    def window_for_day(self, date):
        """Return a TimeWindow for the specified day."""
        min = datetime.datetime.combine(date, self.virtual_midnight)
        max = min + datetime.timedelta(1)
        return self.window_for(min, max)

    def window_for_week(self, date):
        """Return a TimeWindow for the week that contains date."""
        monday = date - datetime.timedelta(date.weekday())
        min = datetime.datetime.combine(monday, self.virtual_midnight)
        max = min + datetime.timedelta(7)
        return self.window_for(min, max)

    def window_for_month(self, date):
        """Return a TimeWindow for the month that contains date."""
        first_of_this_month = first_of_month(date)
        first_of_next_month = next_month(date)
        min = datetime.datetime.combine(
            first_of_this_month, self.virtual_midnight)
        max = datetime.datetime.combine(
            first_of_next_month, self.virtual_midnight)
        return self.window_for(min, max)

    def window_for_date_range(self, min, max):
        """Return a TimeWindow for a specified time interval.

        ``min`` and ``max`` should be datetime.date instances.  The
        interval is closed.
        """
        min = datetime.datetime.combine(min, self.virtual_midnight)
        max = datetime.datetime.combine(max, self.virtual_midnight)
        max = max + datetime.timedelta(1)
        return self.window_for(min, max)

    def raw_append(self, line, need_space):
        """Append a line to the time log file."""
        f = codecs.open(self.filename, "a", encoding='UTF-8')
        if need_space:
            f.write('\n')
        f.write(line + '\n')
        f.close()
        self.last_mtime = self.get_mtime()

    def append(self, entry, now=None):
        """Append a new entry to the time log."""
        if not now:
            now = datetime.datetime.now().replace(second=0, microsecond=0)
        self.check_reload()
        need_space = False
        last = self.last_time()
        if last and different_days(now, last, self.virtual_midnight):
            need_space = True
        self.items.append((now, entry))
        self.window.items.append((now, entry))
        line = '%s: %s' % (now.strftime("%Y-%m-%d %H:%M"), entry)
        self.raw_append(line, need_space)

    def valid_time(self, time):
        """Is this a valid time for a correction?

        Valid times are those between the last timelog entry and now.
        """
        if time > datetime.datetime.now():
            return False
        last = self.last_time()
        if last and time < last:
            return False
        return True

    def parse_correction(self, entry):
        """Recognize a time correction.

        Corrections are entries that begin with a timestamp (HH:MM) or a
        relative number of minutes (-MM).

        Returns a tuple (entry, timestamp).  ``timestamp`` will be None
        if no correction was recognized.  ``entry`` will have the leading
        timestamp stripped.
        """
        now = None
        date_match = re.match(r'(\d\d):(\d\d)\s+', entry)
        delta_match = re.match(r'-([1-9]\d?|1\d\d)\s+', entry)
        if date_match:
            h = int(date_match.group(1))
            m = int(date_match.group(2))
            if 0 <= h < 24 and 0 <= m < 60:
                now = datetime.datetime.combine(self.virtual_today(),
                                                datetime.time(h, m))
                if now.time() < self.virtual_midnight:
                    now += datetime.timedelta(1)
                if self.valid_time(now):
                    entry = entry[date_match.end():]
                else:
                    now = None
        if delta_match:
            seconds = int(delta_match.group()) * 60
            now = datetime.datetime.now().replace(second=0, microsecond=0)
            now += datetime.timedelta(seconds=seconds)
            if self.valid_time(now):
                entry = entry[delta_match.end():]
            else:
                now = None
        return entry, now


class TaskList(object):
    """Task list.

    You can have a list of common tasks in a text file that looks like this

        Arrived **
        Reading mail
        Project1: do some task
        Project2: do some other task
        Project1: do yet another task

    These tasks are grouped by their common prefix (separated with ':').
    Tasks without a ':' are grouped under "Other".

    A TaskList has an attribute 'groups' which is a list of tuples
    (group_name, list_of_group_items).
    """

    other_title = 'Other'

    loading_callback = None
    loaded_callback = None
    error_callback = None

    def __init__(self, filename):
        self.filename = filename
        self.load()

    def check_reload(self):
        """Look at the mtime of tasks.txt, and reload it if necessary.

        Returns True if the file was reloaded.
        """
        mtime = self.get_mtime()
        if mtime != self.last_mtime:
            self.load()
            return True
        else:
            return False

    def get_mtime(self):
        """Return the mtime of self.filename, if it exists.

        Returns None if the file doesn't exist.
        """
        try:
            return os.stat(self.filename).st_mtime
        except OSError:
            return None

    def load(self):
        """Load task list from a file named self.filename."""
        groups = {}
        self.last_mtime = self.get_mtime()
        try:
            with open(self.filename) as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if ':' in line:
                        group, task = [s.strip() for s in line.split(':', 1)]
                    else:
                        group, task = self.other_title, line
                    groups.setdefault(group, []).append(task)
        except IOError:
            pass # the file's not there, so what?
        self.groups = sorted(groups.items())

    def reload(self):
        """Reload the task list."""
        self.load()


class RemoteTaskList(TaskList):
    """Task list stored on a remote server.

    Keeps a cached copy of the list in a local file, so you can use it offline.
    """

    def __init__(self, url, cache_filename):
        self.url = url
        TaskList.__init__(self, cache_filename)
        self.first_time = True

    def check_reload(self):
        """Check whether the task list needs to be reloaded.

        Download the task list if this is the first time, and a cached copy is
        not found.

        Returns True if the file was reloaded.
        """
        if self.first_time:
            self.first_time = False
            if not os.path.exists(self.filename):
                self.download()
                return True
        return TaskList.check_reload(self)

    def download(self):
        """Download the task list from the server."""
        if self.loading_callback:
            self.loading_callback()
        try:
            urllib.urlretrieve(self.url, self.filename)
        except IOError:
            if self.error_callback:
                self.error_callback()
        self.load()
        if self.loaded_callback:
            self.loaded_callback()

    def reload(self):
        """Reload the task list."""
        self.download()


class CSVWriter(object):

    def __init__(self, *args, **kw):
        self._writer = csv.writer(*args, **kw)

    if PY3:
        def writerow(self, row):
            self._writer.writerow(row)
    else:
        def writerow(self, row):
            self._writer.writerow([s.encode('UTF-8') if isinstance(s, unicode)
                                   else s for s in row])

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)
