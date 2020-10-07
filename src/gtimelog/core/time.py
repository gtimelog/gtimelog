import codecs
import collections
import datetime
import re

from gtimelog.core.utils import different_days, get_mtime, virtual_day, parse_timelog, first_of_month, next_month

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

        Returns a tuple consisting of entry title and set of tags.
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

    @staticmethod
    def split_category(entry):
        """Split the entry category from the entry itself.

        Return a tuple (category, task).
        """
        if ': ' in entry:
            cat, tsk = entry.split(': ', 1)
            return cat.strip(), tsk.strip()
        elif entry.endswith(':'):
            return entry.partition(':')[0].strip(), ''
        else:
            return None, entry

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
            cat, task = self.split_category(entry)
            entry_list = entries.get(cat, [])
            entry_list.append((start, task, duration))
            entries[cat] = entry_list
            totals[cat] = totals.get(cat, datetime.timedelta(0)) + duration
        return entries, totals

    def totals(self, tag=None, filter_text=None):
        """Calculate total time of work and slacking entries.

        If optional argument `tag` is given, only compute
        totals for entries marked with the given tag.

        If optional argument `filter_text` is given, only compute
        totals for entries matching the text.

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
            if filter_text is not None and filter_text not in entry:
                continue
            if '***' in entry:
                continue
            elif '**' in entry:
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


class TimeLog(TimeCollection):
    """Time log.

    A time log contains a time window for today, and can add new entries at
    the end.
    """

    def __init__(self, filename, virtual_midnight):
        super(TimeLog, self).__init__(virtual_midnight)
        self.day = self.virtual_today()
        self.filename = filename
        self.last_mtime = get_mtime(self.filename)
        self.reread()

    def virtual_today(self):
        """Return today's date, adjusted for virtual midnight."""
        return virtual_day(datetime.datetime.now(), self.virtual_midnight)

    def check_reload(self):
        """Look at the mtime of timelog.txt, and reload it if necessary.

        Returns True if the file was reloaded.
        """
        mtime = get_mtime(self.filename)
        if mtime != self.last_mtime:
            self.reread()
            return True
        else:
            return False

    def reread(self):
        """Reload the log file."""
        self.last_mtime = get_mtime(self.filename)
        try:
            if hasattr(self.filename, 'read'):
                # accept any file-like object
                # this is a hook for unit tests, really
                self.filename.seek(0)
                self.items = parse_timelog(self.filename)
            else:
                with open(self.filename, 'rb') as f:
                    data = f.read()
                self.items = parse_timelog(data.decode('UTF-8').splitlines())
        except IOError:
            self.items = []
        self.window = self.window_for_day(self.day)

    def window_for(self, minimum, maximum):
        """Return a TimeWindow for a specified time interval.

        ``minimum`` and ``maximum`` should be datetime.datetime instances.  The
        interval is half-open (inclusive at ``minimum``, exclusive at ``maximum``).
        """
        return TimeWindow(self, minimum, maximum)

    def window_for_day(self, date):
        """Return a TimeWindow for the specified day."""
        minimum = datetime.datetime.combine(date, self.virtual_midnight)
        maximum = minimum + datetime.timedelta(1)
        return self.window_for(minimum, maximum)

    def window_for_week(self, date):
        """Return a TimeWindow for the week that contains date."""
        monday = date - datetime.timedelta(date.weekday())
        minimum = datetime.datetime.combine(monday, self.virtual_midnight)
        maximum = minimum + datetime.timedelta(7)
        return self.window_for(minimum, maximum)

    def window_for_month(self, date):
        """Return a TimeWindow for the month that contains date."""
        first_of_this_month = first_of_month(date)
        first_of_next_month = next_month(date)
        minimum = datetime.datetime.combine(
            first_of_this_month, self.virtual_midnight)
        maximum = datetime.datetime.combine(
            first_of_next_month, self.virtual_midnight)
        return self.window_for(minimum, maximum)

    def window_for_date_range(self, minimum, maximum):
        """Return a TimeWindow for a specified time interval.

        ``minimum`` and ``maximum`` should be datetime.date instances.  The
        interval is closed.
        """
        minimum = datetime.datetime.combine(minimum, self.virtual_midnight)
        maximum = datetime.datetime.combine(maximum, self.virtual_midnight) + datetime.timedelta(1)
        return self.window_for(minimum, maximum)

    def raw_append(self, line, need_space):
        """Append a line to the time log file."""
        f = codecs.open(self.filename, "a", encoding='UTF-8')
        if need_space:
            f.write('\n')
        f.write(line + '\n')
        f.close()
        self.last_mtime = get_mtime(self.filename)

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
