"""
Non-GUI bits of gtimelog.
"""

import codecs
import csv
import datetime
import os
import sys
import re
import urllib
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
    m = re.match(r'^(\d+)-(\d+)-(\d+) (\d+):(\d+)$', dt)
    if not m:
        raise ValueError('bad date time: ', dt)
    year, month, day, hour, min = map(int, m.groups())
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


class TimeWindow(object):
    """A window into a time log.

    Reads a time log file and remembers all events that took place between
    min_timestamp and max_timestamp.  Includes events that took place at
    min_timestamp, but excludes events that took place at max_timestamp.

    self.items is a list of (timestamp, event_title) tuples.

    Time intervals between events within the time window form entries that have
    a start time, a stop time, and a duration.  Entry title is the title of the
    event that occurred at the stop time.

    The first event also creates a special "arrival" entry of zero duration.

    Entries that span virtual midnight boundaries are also converted to
    "arrival" entries at their end point.

    The earliest_timestamp attribute contains the first (which should be the
    oldest) timestamp in the file.
    """

    def __init__(self, filename, min_timestamp, max_timestamp,
                 virtual_midnight, callback=None):
        self.filename = filename
        self.min_timestamp = min_timestamp
        self.max_timestamp = max_timestamp
        self.virtual_midnight = virtual_midnight
        self.reread(callback)

    def reread(self, callback=None):
        """Parse the time log file and update self.items.

        Also updates self.earliest_timestamp.
        """
        self.items = []
        self.earliest_timestamp = None
        try:
            # accept any file-like object
            # this is a hook for unit tests, really
            if hasattr(self.filename, 'read'):
                f = self.filename
                f.seek(0)
            else:
                f = codecs.open(self.filename, encoding='UTF-8')
        except IOError:
            return
        line = ''
        for line in f:
            if ': ' not in line:
                continue
            time, entry = line.split(': ', 1)
            try:
                time = parse_datetime(time)
            except ValueError:
                continue
            else:
                entry = entry.strip()
                if callback:
                    callback(entry)
                if self.earliest_timestamp is None:
                    self.earliest_timestamp = time
                if self.min_timestamp <= time < self.max_timestamp:
                    self.items.append((time, entry))
        # There's code that relies on entries being sorted.  The entries really
        # should be already sorted in the file, but sometimes the user edits
        # timelog.txt directly and introduces errors.
        # XXX: instead of quietly resorting them we should inform the user if
        # there are errors
        # Note that we must preserve the relative order of entries with
        # the same timestamp: https://bugs.launchpad.net/gtimelog/+bug/708825
        self.items.sort(key=itemgetter(0))
        f.close()

    def last_time(self):
        """Return the time of the last event (or None if there are no events).
        """
        if not self.items:
            return None
        return self.items[-1][0]

    def all_entries(self):
        """Iterate over all entries.

        Yields (start, stop, duration, entry) tuples.  The first entry
        has a duration of 0.
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
            yield start, stop, duration, entry

    def count_days(self):
        """Count days that have entries."""
        count = 0
        last = None
        for start, stop, duration, entry in self.all_entries():
            if last is None or different_days(last, start,
                                              self.virtual_midnight):
                last = start
                count += 1
        return count

    def last_entry(self):
        """Return the last entry (or None if there are no events).

        It is always true that

            self.last_entry() == list(self.all_entries())[-1]

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
        return start, stop, duration, entry

    def grouped_entries(self, skip_first=True):
        """Return consolidated entries (grouped by entry title).

        Returns two list: work entries and slacking entries.  Slacking
        entries are identified by finding two asterisks in the title.
        Entry lists are sorted, and contain (start, entry, duration) tuples.
        """
        work = {}
        slack = {}
        for start, stop, duration, entry in self.all_entries():
            if skip_first:
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

    def totals(self):
        """Calculate total time of work and slacking entries.

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
        for start, stop, duration, entry in self.all_entries():
            if '**' in entry:
                total_slacking += duration
            else:
                total_work += duration
        return total_work, total_slacking

    def icalendar(self, output):
        """Create an iCalendar file with activities."""
        output.write("BEGIN:VCALENDAR\n")
        output.write("PRODID:-//mg.pov.lt/NONSGML GTimeLog//EN\n")
        output.write("VERSION:2.0\n")
        try:
            import socket
            idhost = socket.getfqdn()
        except: # can it actually ever fail?
            idhost = 'localhost'
        dtstamp = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        for start, stop, duration, entry in self.all_entries():
            output.write("BEGIN:VEVENT\n")
            output.write("UID:%s@%s\n" % (hash((start, stop, entry)), idhost))
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
        work, slack = self.grouped_entries()
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
        for start, stop, duration, entry in self.all_entries():
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
        items = [(day, as_hours(start), as_hours(slacking), as_hours(work))
                  for day, (start, slacking, work) in days.items()]
        items.sort()
        writer.writerows(items)


class Reports(object):
    """Generation of reports."""

    def __init__(self, window):
        self.window = window

    def _categorizing_report(self, output, email, who, subject, period_name,
                             estimated_column=False):
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
        if estimated_column:
            output.write("estimated        actual\n")
        else:
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
                    if estimated_column:
                        output.write(u"  %-46s  %-14s  %s\n" %
                                     (entry, '-',
                                     format_duration_short(duration)))
                    else:
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

    def _plain_report(self, output, email, who, subject, period_name,
                      estimated_column=False):
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
        if estimated_column:
            output.write("estimated       actual\n")
        else:
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
                if estimated_column:
                    output.write(u"%-46s  %-14s  %s\n" %
                                 (entry, '-', format_duration_long(duration)))
                else:
                    output.write(u"%-62s  %s\n" %
                                 (entry, format_duration_long(duration)))
            output.write('\n')
        output.write("Total work done this %s: %s\n" %
                     (period_name, format_duration_long(total_work)))

        if categories:
            self._report_categories(output, categories)

    def weekly_report_categorized(self, output, email, who,
                                  estimated_column=False):
        """Format a weekly report with entries displayed  under categories."""
        week = self.window.min_timestamp.isocalendar()[1]
        subject = u'Weekly report for %s (week %02d)' % (who, week)
        return self._categorizing_report(output, email, who, subject,
                                         period_name='week',
                                         estimated_column=estimated_column)

    def monthly_report_categorized(self, output, email, who,
                                   estimated_column=False):
        """Format a monthly report with entries displayed  under categories."""
        month = self.window.min_timestamp.strftime('%Y/%m')
        subject = u'Monthly report for %s (%s)' % (who, month)
        return self._categorizing_report(output, email, who, subject,
                                         period_name='month',
                                         estimated_column=estimated_column)

    def weekly_report_plain(self, output, email, who, estimated_column=False):
        """Format a weekly report ."""
        week = self.window.min_timestamp.isocalendar()[1]
        subject = u'Weekly report for %s (week %02d)' % (who, week)
        return self._plain_report(output, email, who, subject,
                                  period_name='week',
                                  estimated_column=estimated_column)

    def monthly_report_plain(self, output, email, who, estimated_column=False):
        """Format a monthly report ."""
        month = self.window.min_timestamp.strftime('%Y/%m')
        subject = u'Monthly report for %s (%s)' % (who, month)
        return self._plain_report(output, email, who, subject,
                                  period_name='month',
                                  estimated_column=estimated_column)

    def custom_range_report_categorized(self, output, email, who,
                                        estimated_column=False):
        """Format a custom range report with entries displayed  under categories."""
        min = self.window.min_timestamp.strftime('%Y-%m-%d')
        max = self.window.max_timestamp - datetime.timedelta(1)
        max = max.strftime('%Y-%m-%d')
        subject = u'Custom date range report for %s (%s - %s)' % (who, min, max)
        return self._categorizing_report(output, email, who, subject,
                                         period_name='custom range',
                                         estimated_column=estimated_column)

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
        start, stop, duration, entry = items[0]
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


class TimeLog(object):
    """Time log.

    A time log contains a time window for today, and can add new entries at
    the end.
    """

    def __init__(self, filename, virtual_midnight):
        self.filename = filename
        self.virtual_midnight = virtual_midnight
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
        try:
            return os.stat(self.filename).st_mtime
        except OSError:
            return None

    def reread(self):
        """Reload today's log."""
        self.last_mtime = self.get_mtime()
        self.day = self.virtual_today()
        min = datetime.datetime.combine(self.day, self.virtual_midnight)
        max = min + datetime.timedelta(1)
        self.history = []
        self.window = TimeWindow(self.filename, min, max,
                                 self.virtual_midnight,
                                 callback=self.history.append)
        self.need_space = not self.window.items
        self._cache = {(min, max): self.window}

    def window_for(self, min, max):
        """Return a TimeWindow for a specified time interval."""
        try:
            return self._cache[min, max]
        except KeyError:
            window = TimeWindow(self.filename, min, max, self.virtual_midnight)
            if len(self._cache) > 1000:
                self._cache.clear()
            self._cache[min, max] = window
            return window

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
        min = datetime.datetime.combine(min, self.virtual_midnight)
        max = datetime.datetime.combine(max, self.virtual_midnight)
        max = max + datetime.timedelta(1)
        return self.window_for(min, max)

    def whole_history(self):
        """Return a TimeWindow for the whole history."""
        # XXX I don't like this solution.  Better make the min/max filtering
        # arguments optional in TimeWindow.reread
        return self.window_for(self.window.earliest_timestamp,
                               datetime.datetime.now())

    def raw_append(self, line):
        """Append a line to the time log file."""
        f = codecs.open(self.filename, "a", encoding='UTF-8')
        if self.need_space:
            self.need_space = False
            f.write('\n')
        f.write(line + '\n')
        f.close()
        self.last_mtime = self.get_mtime()

    def append(self, entry, now=None):
        """Append a new entry to the time log."""
        if not now:
            now = datetime.datetime.now().replace(second=0, microsecond=0)
        last = self.window.last_time()
        if last and different_days(now, last, self.virtual_midnight):
            # next day: reset self.window
            self.reread()
        self.window.items.append((now, entry))
        line = '%s: %s' % (now.strftime("%Y-%m-%d %H:%M"), entry)
        self.raw_append(line)
        for (min, max), cached in self._cache.items():
            if cached is not self.window and min <= now < max:
                cached.items.append((now, entry))

    def valid_time(self, time):
        if time > datetime.datetime.now():
            return False
        last = self.window.last_time()
        if last and time < last:
            return False
        return True


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
