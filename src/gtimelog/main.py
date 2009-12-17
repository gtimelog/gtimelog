#!/usr/bin/python
"""
A Gtk+ application for keeping track of time.

$Id$
"""

import re
import os
import csv
import sys
import urllib
import datetime
import tempfile
import ConfigParser

import pygtk
pygtk.require('2.0')
import gobject
import gtk
import gtk.glade
import pango

from gtimelog import __version__


# support very old Python versions that nobody probably uses any more
try:
    set
except NameError:
    from sets import Set as set


# This is to let people run GTimeLog without having to install it
resource_dir = os.path.dirname(os.path.realpath(__file__))
ui_file = os.path.join(resource_dir, "gtimelog.glade")
icon_file = os.path.join(resource_dir, "gtimelog-small.png")

# This is for distribution packages
if not os.path.exists(ui_file):
    ui_file = "/usr/share/gtimelog/gtimelog.glade"
if not os.path.exists(icon_file):
    icon_file = "/usr/share/pixmaps/gtimelog-small.png"


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
                f = open(self.filename)
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
        # The entries really should be already sorted in the file
        # XXX: instead of quietly resorting them we should inform the user
        self.items.sort() # there's code that relies on them being sorted
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
        work = work.values()
        work.sort()
        slack = slack.values()
        slack.sort()
        return work, slack

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
        print >> output, "BEGIN:VCALENDAR"
        print >> output, "PRODID:-//mg.pov.lt/NONSGML GTimeLog//EN"
        print >> output, "VERSION:2.0"
        try:
            import socket
            idhost = socket.getfqdn()
        except: # can it actually ever fail?
            idhost = 'localhost'
        dtstamp = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        for start, stop, duration, entry in self.all_entries():
            print >> output, "BEGIN:VEVENT"
            print >> output, "UID:%s@%s" % (hash((start, stop, entry)), idhost)
            print >> output, "SUMMARY:%s" % (entry.replace('\\', '\\\\')
                                                  .replace(';', '\\;')
                                                  .replace(',', '\\,'))
            print >> output, "DTSTART:%s" % start.strftime('%Y%m%dT%H%M%S')
            print >> output, "DTEND:%s" % stop.strftime('%Y%m%dT%H%M%S')
            print >> output, "DTSTAMP:%s" % dtstamp
            print >> output, "END:VEVENT"
        print >> output, "END:VCALENDAR"

    def to_csv_complete(self, output, title_row=True):
        """Export work entries to a CSV file.

        The file has two columns: task title and time (in minutes).
        """
        writer = csv.writer(output)
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
        writer = csv.writer(output)
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

    def daily_report(self, output, email, who):
        """Format a daily report.

        Writes a daily report template in RFC-822 format to output.
        """
        # Locale is set as a side effect of 'import gtk', so strftime('%a')
        # would give us translated names
        weekday_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        weekday = weekday_names[self.min_timestamp.weekday()]
        week = self.min_timestamp.strftime('%V')
        print >> output, "To: %(email)s" % {'email': email}
        print >> output, ("Subject: %(date)s report for %(who)s"
                          " (%(weekday)s, week %(week)s)"
                          % {'date': self.min_timestamp.strftime('%Y-%m-%d'),
                             'weekday': weekday, 'week': week, 'who': who})
        print >> output
        items = list(self.all_entries())
        if not items:
            print >> output, "No work done today."
            return
        start, stop, duration, entry = items[0]
        entry = entry[:1].upper() + entry[1:]
        print >> output, "%s at %s" % (entry, start.strftime('%H:%M'))
        print >> output
        work, slack = self.grouped_entries()
        total_work, total_slacking = self.totals()
        if work:
            for start, entry, duration in work:
                entry = entry[:1].upper() + entry[1:]
                print >> output, u"%-62s  %s" % (entry,
                                                format_duration_long(duration))
            print >> output
        print >> output, ("Total work done: %s" %
                          format_duration_long(total_work))
        print >> output
        if slack:
            for start, entry, duration in slack:
                entry = entry[:1].upper() + entry[1:]
                print >> output, u"%-62s  %s" % (entry,
                                                format_duration_long(duration))
            print >> output
        print >> output, ("Time spent slacking: %s" %
                          format_duration_long(total_slacking))

    def weekly_report(self, output, email, who, estimated_column=False):
        """Format a weekly report.

        Writes a weekly report template in RFC-822 format to output.
        """
        week = self.min_timestamp.strftime('%V')
        print >> output, "To: %(email)s" % {'email': email}
        print >> output, "Subject: Weekly report for %s (week %s)" % (who,
                                                                      week)
        print >> output
        items = list(self.all_entries())
        if not items:
            print >> output, "No work done this week."
            return
        print >> output, " " * 46,
        if estimated_column:
            print >> output, "estimated       actual"
        else:
            print >> output, "                time"
        work, slack = self.grouped_entries()
        total_work, total_slacking = self.totals()
        if work:
            work = [(entry, duration) for start, entry, duration in work]
            work.sort()
            for entry, duration in work:
                if not duration:
                    continue # skip empty "arrival" entries
                entry = entry[:1].upper() + entry[1:]
                if estimated_column:
                    print >> output, (u"%-46s  %-14s  %s" %
                                (entry, '-', format_duration_long(duration)))
                else:
                    print >> output, (u"%-62s  %s" %
                                (entry, format_duration_long(duration)))
            print >> output
        print >> output, ("Total work done this week: %s" %
                          format_duration_long(total_work))

    def monthly_report(self, output, email, who):
        """Format a monthly report.

        Writes a monthly report template in RFC-822 format to output.
        """

        month = self.min_timestamp.strftime('%Y/%m')
        print >> output, "To: %(email)s" % {'email': email}
        print >> output, "Subject: Monthly report for %s (%s)" % (who, month)
        print >> output

        items = list(self.all_entries())
        if not items:
            print >> output, "No work done this month."
            return

        print >> output, " " * 46

        work, slack = self.grouped_entries()
        total_work, total_slacking = self.totals()
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
                print >> output, (u"%-62s  %s" %
                    (entry, format_duration_long(duration)))
            print >> output

        print >> output, ("Total work done this month: %s" %
                          format_duration_long(total_work))

        if categories:
            print >> output
            print >> output, "By category:"
            print >> output

            items = categories.items()
            items.sort()
            for cat, duration in items:
                if not cat:
                    continue

                print >> output, u"%-62s  %s" % (
                    cat, format_duration_long(duration))

            if None in categories:
                print >> output, u"%-62s  %s" % (
                    '(none)', format_duration_long(categories[None]))
            print >> output


class TimeLog(object):
    """Time log.

    A time log contains a time window for today, and can add new entries at
    the end.
    """

    def __init__(self, filename, virtual_midnight):
        self.filename = filename
        self.virtual_midnight = virtual_midnight
        self.reread()

    def reread(self):
        """Reload today's log."""
        self.day = virtual_day(datetime.datetime.now(), self.virtual_midnight)
        min = datetime.datetime.combine(self.day, self.virtual_midnight)
        max = min + datetime.timedelta(1)
        self.history = []
        self.window = TimeWindow(self.filename, min, max,
                                 self.virtual_midnight,
                                 callback=self.history.append)
        self.need_space = not self.window.items

    def window_for(self, min, max):
        """Return a TimeWindow for a specified time interval."""
        return TimeWindow(self.filename, min, max, self.virtual_midnight)

    def whole_history(self):
        """Return a TimeWindow for the whole history."""
        # XXX I don't like this solution.  Better make the min/max filtering
        # arguments optional in TimeWindow.reread
        return self.window_for(self.window.earliest_timestamp,
                               datetime.datetime.now())

    def raw_append(self, line):
        """Append a line to the time log file."""
        f = open(self.filename, "a")
        if self.need_space:
            self.need_space = False
            print >> f
        print >> f, line
        f.close()

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
        """Return the mtime of self.filename, or None if the file doesn't exist."""
        try:
            return os.stat(self.filename).st_mtime
        except OSError:
            return None

    def load(self):
        """Load task list from a file named self.filename."""
        groups = {}
        self.last_mtime = self.get_mtime()
        try:
            for line in file(self.filename):
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
        self.groups = groups.items()
        self.groups.sort()

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


class Settings(object):
    """Configurable settings for GTimeLog."""

    # Insane defaults
    email = 'activity-list@example.com'
    name = 'Anonymous'

    editor = 'gvim'
    mailer = 'x-terminal-emulator -e mutt -H %s'
    spreadsheet = 'oocalc %s'

    enable_gtk_completion = True  # False enables gvim-style completion

    hours = 8
    virtual_midnight = datetime.time(2, 0)

    task_list_url = ''
    edit_task_list_cmd = ''

    show_office_hours = True
    show_tray_icon = True
    prefer_old_tray_icon = True

    def _config(self):
        config = ConfigParser.RawConfigParser()
        config.add_section('gtimelog')
        config.set('gtimelog', 'list-email', self.email)
        config.set('gtimelog', 'name', self.name)
        config.set('gtimelog', 'editor', self.editor)
        config.set('gtimelog', 'mailer', self.mailer)
        config.set('gtimelog', 'spreadsheet', self.spreadsheet)
        config.set('gtimelog', 'gtk-completion',
                   str(self.enable_gtk_completion))
        config.set('gtimelog', 'hours', str(self.hours))
        config.set('gtimelog', 'virtual_midnight',
                   self.virtual_midnight.strftime('%H:%M'))
        config.set('gtimelog', 'task_list_url', self.task_list_url)
        config.set('gtimelog', 'edit_task_list_cmd', self.edit_task_list_cmd)
        config.set('gtimelog', 'show_office_hours',
                   str(self.show_office_hours))
        config.set('gtimelog', 'show_tray_icon', str(self.show_tray_icon))
        config.set('gtimelog', 'prefer_old_tray_icon', str(self.prefer_old_tray_icon))
        return config

    def load(self, filename):
        config = self._config()
        config.read([filename])
        self.email = config.get('gtimelog', 'list-email')
        self.name = config.get('gtimelog', 'name')
        self.editor = config.get('gtimelog', 'editor')
        self.mailer = config.get('gtimelog', 'mailer')
        self.spreadsheet = config.get('gtimelog', 'spreadsheet')
        self.enable_gtk_completion = config.getboolean('gtimelog',
                                                       'gtk-completion')
        self.hours = config.getfloat('gtimelog', 'hours')
        self.virtual_midnight = parse_time(config.get('gtimelog',
                                                      'virtual_midnight'))
        self.task_list_url = config.get('gtimelog', 'task_list_url')
        self.edit_task_list_cmd = config.get('gtimelog', 'edit_task_list_cmd')
        self.show_office_hours = config.getboolean('gtimelog',
                                                   'show_office_hours')
        self.show_tray_icon = config.getboolean('gtimelog', 'show_tray_icon')
        self.prefer_old_tray_icon = config.getboolean('gtimelog',
                                                      'prefer_old_tray_icon')

    def save(self, filename):
        config = self._config()
        f = file(filename, 'w')
        try:
            config.write(f)
        finally:
            f.close()


class SimpleStatusIcon(object):
    """Status icon for gtimelog in the notification area."""

    def __init__(self, gtimelog_window):
        self.gtimelog_window = gtimelog_window
        self.timelog = gtimelog_window.timelog
        self.trayicon = None
        if not hasattr(gtk, 'StatusIcon'):
            # you must be using a very old PyGtk
            return
        self.icon = gtk.status_icon_new_from_file(icon_file)
        self.last_tick = False
        self.tick()
        self.icon.connect("activate", self.on_activate)
        self.icon.connect("popup-menu", self.on_popup_menu)
        gobject.timeout_add(1000, self.tick)
        self.gtimelog_window.entry_watchers.append(self.entry_added)
        self.gtimelog_window.tray_icon = self

    def available(self):
        """Is the icon supported by this system?

        SimpleStatusIcon needs PyGtk 2.10 or newer
        """
        return self.icon is not None

    def on_activate(self, widget):
        """The user clicked on the icon."""
        main_window = self.gtimelog_window.main_window
        if main_window.get_property("visible"):
           main_window.hide()
        else:
           main_window.present()

    def on_popup_menu(self, widget, button, activate_time):
        """The user clicked on the icon."""
        main_window = self.gtimelog_window.main_window
        if main_window.get_property("visible"):
            self.gtimelog_window.tray_show.hide()
            self.gtimelog_window.tray_hide.show()
        else:
            self.gtimelog_window.tray_show.show()
            self.gtimelog_window.tray_hide.hide()
        tray_icon_popup_menu = self.gtimelog_window.tray_icon_popup_menu
        tray_icon_popup_menu.popup(None, None, gtk.status_icon_position_menu,
                                   button, activate_time, self.icon)

    def entry_added(self, entry):
        """An entry has been added."""
        self.tick()

    def tick(self):
        """Tick every second."""
        self.icon.set_tooltip(self.tip())
        return True

    def tip(self):
        """Compute tooltip text."""
        current_task = self.gtimelog_window.task_entry.get_text()
        if not current_task:
            current_task = "nothing"
        tip = "GTimeLog: working on %s" % current_task
        total_work, total_slacking = self.timelog.window.totals()
        tip += "\nWork done today: %s" % format_duration(total_work)
        time_left = self.gtimelog_window.time_left_at_work(total_work)
        if time_left is not None:
            if time_left < datetime.timedelta(0):
                time_left = datetime.timedelta(0)
            tip += "\nTime left at work: %s" % format_duration(time_left)
        return tip


class OldTrayIcon(object):
    """Old tray icon for gtimelog, shows a ticking clock.
    
    Uses the old and deprecated egg.trayicon module.
    """

    def __init__(self, gtimelog_window):
        self.gtimelog_window = gtimelog_window
        self.timelog = gtimelog_window.timelog
        self.trayicon = None
        try:
            import egg.trayicon
        except ImportError:
            return # nothing to do here, move along
                   # or install python-gnome2-extras
        self.tooltips = gtk.Tooltips()
        self.eventbox = gtk.EventBox()
        hbox = gtk.HBox()
        icon = gtk.Image()
        icon.set_from_file(icon_file)
        hbox.add(icon)
        self.time_label = gtk.Label()
        hbox.add(self.time_label)
        self.eventbox.add(hbox)
        self.trayicon = egg.trayicon.TrayIcon("GTimeLog")
        self.trayicon.add(self.eventbox)
        self.last_tick = False
        self.tick(force_update=True)
        self.trayicon.show_all()
        tray_icon_popup_menu = gtimelog_window.tray_icon_popup_menu
        self.eventbox.connect_object("button-press-event", self.on_press,
                                     tray_icon_popup_menu)
        self.eventbox.connect("button-release-event", self.on_release)
        gobject.timeout_add(1000, self.tick)
        self.gtimelog_window.entry_watchers.append(self.entry_added)
        self.gtimelog_window.tray_icon = self

    def available(self):
        """Is the icon supported by this system?

        OldTrayIcon needs egg.trayicon, which is now deprecated and likely
        no longer available in modern Linux distributions.
        """
        return self.trayicon is not None

    def on_press(self, widget, event):
        """A mouse button was pressed on the tray icon label."""
        if event.button != 3:
            return
        main_window = self.gtimelog_window.main_window
        if main_window.get_property("visible"):
            self.gtimelog_window.tray_show.hide()
            self.gtimelog_window.tray_hide.show()
        else:
            self.gtimelog_window.tray_show.show()
            self.gtimelog_window.tray_hide.hide()
        widget.popup(None, None, None, event.button, event.time)

    def on_release(self, widget, event):
        """A mouse button was released on the tray icon label."""
        if event.button != 1:
            return
        main_window = self.gtimelog_window.main_window
        if main_window.get_property("visible"):
           main_window.hide()
        else:
           main_window.present()

    def entry_added(self, entry):
        """An entry has been added."""
        self.tick(force_update=True)

    def tick(self, force_update=False):
        """Tick every second."""
        now = datetime.datetime.now().replace(second=0, microsecond=0)
        if now != self.last_tick or force_update: # Do not eat CPU too much
            self.last_tick = now
            last_time = self.timelog.window.last_time()
            if last_time is None:
                self.time_label.set_text(now.strftime("%H:%M"))
            else:
                self.time_label.set_text(format_duration_short(now - last_time))
        self.tooltips.set_tip(self.trayicon, self.tip())
        return True

    def tip(self):
        """Compute tooltip text."""
        current_task = self.gtimelog_window.task_entry.get_text()
        if not current_task:
            current_task = "nothing"
        tip = "GTimeLog: working on %s" % current_task
        total_work, total_slacking = self.timelog.window.totals()
        tip += "\nWork done today: %s" % format_duration(total_work)
        time_left = self.gtimelog_window.time_left_at_work(total_work)
        if time_left is not None:
            if time_left < datetime.timedelta(0):
                time_left = datetime.timedelta(0)
            tip += "\nTime left at work: %s" % format_duration(time_left)
        return tip


class MainWindow(object):
    """Main application window."""

    # Initial view mode
    chronological = True
    show_tasks = True

    # URL to use for Help -> Online Documentation
    help_url = "http://mg.pov.lt/gtimelog"

    def __init__(self, timelog, settings, tasks):
        """Create the main window."""
        self.timelog = timelog
        self.settings = settings
        self.tasks = tasks
        self.tray_icon = None
        self.last_tick = None
        self.footer_mark = None
        # Try to prevent timer routines mucking with the buffer while we're
        # mucking with the buffer.  Not sure if it is necessary.
        self.lock = False
        self.entry_watchers = []
        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        tree = gtk.glade.XML(ui_file)
        # Set initial state of menu items *before* we hook up signals
        chronological_menu_item = tree.get_widget("chronological")
        chronological_menu_item.set_active(self.chronological)
        show_task_pane_item = tree.get_widget("show_task_pane")
        show_task_pane_item.set_active(self.show_tasks)
        # Now hook up signals
        tree.signal_autoconnect(self)
        # Store references to UI elements we're going to need later
        self.tray_icon_popup_menu = tree.get_widget("tray_icon_popup_menu")
        self.tray_show = tree.get_widget("tray_show")
        self.tray_hide = tree.get_widget("tray_hide")
        self.about_dialog = tree.get_widget("about_dialog")
        self.about_dialog_ok_btn = tree.get_widget("ok_button")
        self.about_dialog_ok_btn.connect("clicked", self.close_about_dialog)
        self.about_text = tree.get_widget("about_text")
        self.about_text.set_markup(self.about_text.get_label() %
                                   dict(version=__version__))
        self.calendar_dialog = tree.get_widget("calendar_dialog")
        self.calendar = tree.get_widget("calendar")
        self.calendar.connect("day_selected_double_click",
                              self.on_calendar_day_selected_double_click)
        self.main_window = tree.get_widget("main_window")
        self.main_window.connect("delete_event", self.delete_event)
        self.log_view = tree.get_widget("log_view")
        self.set_up_log_view_columns()
        self.task_pane = tree.get_widget("task_list_pane")
        if not self.show_tasks:
            self.task_pane.hide()
        self.task_pane_info_label = tree.get_widget("task_pane_info_label")
        self.tasks.loading_callback = self.task_list_loading
        self.tasks.loaded_callback = self.task_list_loaded
        self.tasks.error_callback = self.task_list_error
        self.task_list = tree.get_widget("task_list")
        self.task_store = gtk.TreeStore(str, str)
        self.task_list.set_model(self.task_store)
        column = gtk.TreeViewColumn("Task", gtk.CellRendererText(), text=0)
        self.task_list.append_column(column)
        self.task_list.connect("row_activated", self.task_list_row_activated)
        self.task_list_popup_menu = tree.get_widget("task_list_popup_menu")
        self.task_list.connect_object("button_press_event",
                                      self.task_list_button_press,
                                      self.task_list_popup_menu)
        task_list_edit_menu_item = tree.get_widget("task_list_edit")
        if not self.settings.edit_task_list_cmd:
            task_list_edit_menu_item.set_sensitive(False)
        self.time_label = tree.get_widget("time_label")
        self.task_entry = tree.get_widget("task_entry")
        self.task_entry.connect("changed", self.task_entry_changed)
        self.task_entry.connect("key_press_event", self.task_entry_key_press)
        self.add_button = tree.get_widget("add_button")
        self.add_button.connect("clicked", self.add_entry)
        buffer = self.log_view.get_buffer()
        self.log_buffer = buffer
        buffer.create_tag('today', foreground='blue')
        buffer.create_tag('duration', foreground='red')
        buffer.create_tag('time', foreground='green')
        buffer.create_tag('slacking', foreground='gray')
        self.set_up_task_list()
        self.set_up_completion()
        self.set_up_history()
        self.populate_log()
        self.tick(True)
        gobject.timeout_add(1000, self.tick)

    def set_up_log_view_columns(self):
        """Set up tab stops in the log view."""
        pango_context = self.log_view.get_pango_context()
        em = pango_context.get_font_description().get_size()
        tabs = pango.TabArray(2, False)
        tabs.set_tab(0, pango.TAB_LEFT, 9 * em)
        tabs.set_tab(1, pango.TAB_LEFT, 12 * em)
        self.log_view.set_tabs(tabs)

    def w(self, text, tag=None):
        """Write some text at the end of the log buffer."""
        buffer = self.log_buffer
        if tag:
            buffer.insert_with_tags_by_name(buffer.get_end_iter(), text, tag)
        else:
            buffer.insert(buffer.get_end_iter(), text)

    def populate_log(self):
        """Populate the log."""
        self.lock = True
        buffer = self.log_buffer
        buffer.set_text("")
        if self.footer_mark is not None:
            buffer.delete_mark(self.footer_mark)
            self.footer_mark = None
        today = virtual_day(datetime.datetime.now(),
                            self.timelog.virtual_midnight)
        today = today.strftime('%A, %Y-%m-%d (week %V)')
        self.w(today + '\n\n', 'today')
        if self.chronological:
            for item in self.timelog.window.all_entries():
                self.write_item(item)
        else:
            work, slack = self.timelog.window.grouped_entries()
            for start, entry, duration in work + slack:
                self.write_group(entry, duration)
            where = buffer.get_end_iter()
            where.backward_cursor_position()
            buffer.place_cursor(where)
        self.add_footer()
        self.scroll_to_end()
        self.lock = False

    def delete_footer(self):
        buffer = self.log_buffer
        buffer.delete(buffer.get_iter_at_mark(self.footer_mark),
                      buffer.get_end_iter())
        buffer.delete_mark(self.footer_mark)
        self.footer_mark = None

    def add_footer(self):
        buffer = self.log_buffer
        self.footer_mark = buffer.create_mark('footer', buffer.get_end_iter(),
                                              True)
        total_work, total_slacking = self.timelog.window.totals()
        weekly_window = self.weekly_window()
        week_total_work, week_total_slacking = weekly_window.totals()
        work_days_this_week = weekly_window.count_days()

        self.w('\n')
        self.w('Total work done: ')
        self.w(format_duration(total_work), 'duration')
        self.w(' (')
        self.w(format_duration(week_total_work), 'duration')
        self.w(' this week')
        if work_days_this_week:
            per_diem = week_total_work / work_days_this_week
            self.w(', ')
            self.w(format_duration(per_diem), 'duration')
            self.w(' per day')
        self.w(')\n')
        self.w('Total slacking: ')
        self.w(format_duration(total_slacking), 'duration')
        self.w(' (')
        self.w(format_duration(week_total_slacking), 'duration')
        self.w(' this week')
        if work_days_this_week:
            per_diem = week_total_slacking / work_days_this_week
            self.w(', ')
            self.w(format_duration(per_diem), 'duration')
            self.w(' per day')
        self.w(')\n')
        time_left = self.time_left_at_work(total_work)
        if time_left is not None:
            time_to_leave = datetime.datetime.now() + time_left
            if time_left < datetime.timedelta(0):
                time_left = datetime.timedelta(0)
            self.w('Time left at work: ')
            self.w(format_duration(time_left), 'duration')
            self.w(' (till ')
            self.w(time_to_leave.strftime('%H:%M'), 'time')
            self.w(')')

        if self.settings.show_office_hours:
            self.w('\nAt office today: ')
            hours = datetime.timedelta(hours=self.settings.hours)
            total = total_slacking + total_work
            self.w("%s " % format_duration(total), 'duration' )
            self.w('(')
            if total > hours:
                self.w(format_duration(total - hours), 'duration')
                self.w(' overtime')
            else:
                self.w(format_duration(hours - total), 'duration')
                self.w(' left')
            self.w(')')

    def time_left_at_work(self, total_work):
        """Calculate time left to work."""
        last_time = self.timelog.window.last_time()
        if last_time is None:
            return None
        now = datetime.datetime.now()
        current_task = self.task_entry.get_text()
        current_task_time = now - last_time
        if '**' in current_task:
            total_time = total_work
        else:
            total_time = total_work + current_task_time
        return datetime.timedelta(hours=self.settings.hours) - total_time

    def write_item(self, item):
        buffer = self.log_buffer
        start, stop, duration, entry = item
        self.w(format_duration(duration), 'duration')
        period = '\t(%s-%s)\t' % (start.strftime('%H:%M'),
                                  stop.strftime('%H:%M'))
        self.w(period, 'time')
        tag = '**' in entry and 'slacking' or None
        self.w(entry + '\n', tag)
        where = buffer.get_end_iter()
        where.backward_cursor_position()
        buffer.place_cursor(where)

    def write_group(self, entry, duration):
        self.w(format_duration(duration), 'duration')
        tag = '**' in entry and 'slacking' or None
        self.w('\t' + entry + '\n', tag)

    def scroll_to_end(self):
        buffer = self.log_view.get_buffer()
        end_mark = buffer.create_mark('end', buffer.get_end_iter())
        self.log_view.scroll_to_mark(end_mark, 0)
        buffer.delete_mark(end_mark)

    def set_up_task_list(self):
        """Set up the task list pane."""
        self.task_store.clear()
        for group_name, group_items in self.tasks.groups:
            t = self.task_store.append(None, [group_name, group_name + ': '])
            for item in group_items:
                if group_name == self.tasks.other_title:
                    task = item
                else:
                    task = group_name + ': ' + item
                self.task_store.append(t, [item, task])
        self.task_list.expand_all()

    def set_up_history(self):
        """Set up history."""
        self.history = self.timelog.history
        self.filtered_history = []
        self.history_pos = 0
        self.history_undo = ''
        if not self.have_completion:
            return
        seen = set()
        self.completion_choices.clear()
        for entry in self.history:
            if entry not in seen:
                seen.add(entry)
                self.completion_choices.append([entry])

    def set_up_completion(self):
        """Set up autocompletion."""
        if not self.settings.enable_gtk_completion:
            self.have_completion = False
            return
        self.have_completion = hasattr(gtk, 'EntryCompletion')
        if not self.have_completion:
            return
        self.completion_choices = gtk.ListStore(str)
        completion = gtk.EntryCompletion()
        completion.set_model(self.completion_choices)
        completion.set_text_column(0)
        self.task_entry.set_completion(completion)

    def add_history(self, entry):
        """Add an entry to history."""
        self.history.append(entry)
        self.history_pos = 0
        if not self.have_completion:
            return
        if entry not in [row[0] for row in self.completion_choices]:
            self.completion_choices.append([entry])

    def delete_event(self, widget, data=None):
        """Try to close the window."""
        if self.tray_icon:
            self.main_window.hide()
            return True
        else:
            gtk.main_quit()
            return False

    def close_about_dialog(self, widget):
        """Ok clicked in the about dialog."""
        self.about_dialog.hide()

    def on_show_activate(self, widget):
        """Tray icon menu -> Show selected"""
        self.main_window.present()

    def on_hide_activate(self, widget):
        """Tray icon menu -> Hide selected"""
        self.main_window.hide()

    def on_quit_activate(self, widget):
        """File -> Quit selected"""
        gtk.main_quit()

    def on_about_activate(self, widget):
        """Help -> About selected"""
        self.about_dialog.show()

    def on_online_help_activate(self, widget):
        """Help -> Online Documentation selected"""
        import webbrowser
        webbrowser.open(self.help_url)

    def on_chronological_activate(self, widget):
        """View -> Chronological"""
        self.chronological = True
        self.populate_log()

    def on_grouped_activate(self, widget):
        """View -> Grouped"""
        self.chronological = False
        self.populate_log()

    def on_daily_report_activate(self, widget):
        """File -> Daily Report"""
        window = self.timelog.window
        self.mail(window.daily_report)

    def on_yesterdays_report_activate(self, widget):
        """File -> Daily Report for Yesterday"""
        max = self.timelog.window.min_timestamp
        min = max - datetime.timedelta(1)
        window = self.timelog.window_for(min, max)
        self.mail(window.daily_report)

    def on_previous_day_report_activate(self, widget):
        """File -> Daily Report for a Previous Day"""
        day = self.choose_date()
        if day:
            min = datetime.datetime.combine(day,
                            self.timelog.virtual_midnight)
            max = min + datetime.timedelta(1)
            window = self.timelog.window_for(min, max)
            self.mail(window.daily_report)

    def choose_date(self):
        """Pop up a calendar dialog.

        Returns either a datetime.date, or one.
        """
        if self.calendar_dialog.run() == gtk.RESPONSE_OK:
            y, m1, d = self.calendar.get_date()
            day = datetime.date(y, m1+1, d)
        else:
            day = None
        self.calendar_dialog.hide()
        return day

    def on_calendar_day_selected_double_click(self, widget):
        """Double-click on a calendar day: close the dialog."""
        self.calendar_dialog.response(gtk.RESPONSE_OK)

    def weekly_window(self, day=None):
        if not day:
            day = self.timelog.day
        monday = day - datetime.timedelta(day.weekday())
        min = datetime.datetime.combine(monday,
                        self.timelog.virtual_midnight)
        max = min + datetime.timedelta(7)
        window = self.timelog.window_for(min, max)
        return window

    def on_weekly_report_activate(self, widget):
        """File -> Weekly Report"""
        window = self.weekly_window()
        self.mail(window.weekly_report)

    def on_last_weeks_report_activate(self, widget):
        """File -> Weekly Report for Last Week"""
        day = self.timelog.day - datetime.timedelta(7)
        window = self.weekly_window(day=day)
        self.mail(window.weekly_report)

    def on_previous_week_report_activate(self, widget):
        """File -> Weekly Report for a Previous Week"""
        day = self.choose_date()
        if day:
            window = self.weekly_window(day=day)
            self.mail(window.weekly_report)

    def monthly_window(self, day=None):
        if not day:
            day = self.timelog.day
        first_of_this_month = first_of_month(day)
        first_of_next_month = next_month(day)
        min = datetime.datetime.combine(first_of_this_month,
                                        self.timelog.virtual_midnight)
        max = datetime.datetime.combine(first_of_next_month,
                                        self.timelog.virtual_midnight)
        window = self.timelog.window_for(min, max)
        return window

    def on_previous_month_report_activate(self, widget):
        """File -> Monthly Report for a Previous Month"""
        day = self.choose_date()
        if day:
            window = self.monthly_window(day=day)
            self.mail(window.monthly_report)

    def on_last_month_report_activate(self, widget):
        """File -> Monthly Report for Last Month"""
        day = self.timelog.day - datetime.timedelta(self.timelog.day.day)
        window = self.monthly_window(day=day)
        self.mail(window.monthly_report)

    def on_monthly_report_activate(self, widget):
        """File -> Monthly Report"""
        window = self.monthly_window()
        self.mail(window.monthly_report)

    def on_open_complete_spreadsheet_activate(self, widget):
        """Report -> Complete Report in Spreadsheet"""
        tempfn = tempfile.mktemp(suffix='gtimelog.csv') # XXX unsafe!
        f = open(tempfn, 'w')
        self.timelog.whole_history().to_csv_complete(f)
        f.close()
        self.spawn(self.settings.spreadsheet, tempfn)

    def on_open_slack_spreadsheet_activate(self, widget):
        """Report -> Work/_Slacking stats in Spreadsheet"""
        tempfn = tempfile.mktemp(suffix='gtimelog.csv') # XXX unsafe!
        f = open(tempfn, 'w')
        self.timelog.whole_history().to_csv_daily(f)
        f.close()
        self.spawn(self.settings.spreadsheet, tempfn)

    def on_edit_timelog_activate(self, widget):
        """File -> Edit timelog.txt"""
        self.spawn(self.settings.editor, '"%s"' % self.timelog.filename)

    def mail(self, write_draft):
        """Send an email."""
        draftfn = tempfile.mktemp(suffix='gtimelog') # XXX unsafe!
        draft = open(draftfn, 'w')
        write_draft(draft, self.settings.email, self.settings.name)
        draft.close()
        self.spawn(self.settings.mailer, draftfn)
        # XXX rm draftfn when done -- but how?

    def spawn(self, command, arg=None):
        """Spawn a process in background"""
        # XXX shell-escape arg, please.
        if arg is not None:
            if '%s' in command:
                command = command % arg
            else:
                command += ' ' + arg
        os.system(command + " &")

    def on_reread_activate(self, widget):
        """File -> Reread"""
        self.timelog.reread()
        self.set_up_history()
        self.populate_log()
        self.tick(True)

    def on_show_task_pane_toggled(self, event):
        """View -> Tasks"""
        if self.task_pane.get_property("visible"):
            self.task_pane.hide()
        else:
            self.task_pane.show()

    def task_list_row_activated(self, treeview, path, view_column):
        """A task was selected in the task pane -- put it to the entry."""
        model = treeview.get_model()
        task = model[path][1]
        self.task_entry.set_text(task)
        self.task_entry.grab_focus()
        self.task_entry.set_position(-1)
        # XXX: how does this integrate with history?

    def task_list_button_press(self, menu, event):
        if event.button == 3:
            menu.popup(None, None, None, event.button, event.time)
            return True
        else:
            return False

    def on_task_list_reload(self, event):
        self.tasks.reload()
        self.set_up_task_list()

    def on_task_list_edit(self, event):
        self.spawn(self.settings.edit_task_list_cmd)

    def task_list_loading(self):
        self.task_list_loading_failed = False
        self.task_pane_info_label.set_text("Loading...")
        self.task_pane_info_label.show()
        # let the ui update become visible
        while gtk.events_pending():
            gtk.main_iteration()

    def task_list_error(self):
        self.task_list_loading_failed = True
        self.task_pane_info_label.set_text("Could not get task list.")
        self.task_pane_info_label.show()

    def task_list_loaded(self):
        if not self.task_list_loading_failed:
            self.task_pane_info_label.hide()

    def task_entry_changed(self, widget):
        """Reset history position when the task entry is changed."""
        self.history_pos = 0

    def task_entry_key_press(self, widget, event):
        """Handle key presses in task entry."""
        if event.keyval == gtk.gdk.keyval_from_name('Prior'):
            self._do_history(1)
            return True
        if event.keyval == gtk.gdk.keyval_from_name('Next'):
            self._do_history(-1)
            return True
        # XXX This interferes with the completion box.  How do I determine
        # whether the completion box is visible or not?
        if self.have_completion:
            return False
        if event.keyval == gtk.gdk.keyval_from_name('Up'):
            self._do_history(1)
            return True
        if event.keyval == gtk.gdk.keyval_from_name('Down'):
            self._do_history(-1)
            return True
        return False

    def _do_history(self, delta):
        """Handle movement in history."""
        if not self.history:
            return
        if self.history_pos == 0:
            self.history_undo = self.task_entry.get_text()
            self.filtered_history = uniq([l for l in self.history
                                          if l.startswith(self.history_undo)])
        history = self.filtered_history
        new_pos = max(0, min(self.history_pos + delta, len(history)))
        if new_pos == 0:
            self.task_entry.set_text(self.history_undo)
            self.task_entry.set_position(-1)
        else:
            self.task_entry.set_text(history[-new_pos])
            self.task_entry.select_region(0, -1)
        # Do this after task_entry_changed reset history_pos to 0
        self.history_pos = new_pos

    def add_entry(self, widget, data=None):
        """Add the task entry to the log."""
        entry = self.task_entry.get_text()

        now = None
        date_match = re.match(r'(\d\d):(\d\d)\s+', entry)
        delta_match = re.match(r'-([1-9]\d?|1\d\d)\s+', entry)
        if date_match:
            h = int(date_match.group(1))
            m = int(date_match.group(2))
            if 0 <= h < 24 and 0 <= m <= 60:
                now = datetime.datetime.now()
                now = now.replace(hour=h, minute=m, second=0, microsecond=0)
                if self.timelog.valid_time(now):
                    entry = entry[date_match.end():]
                else:
                    now = None
        if delta_match:
            seconds = int(delta_match.group()) * 60
            now = datetime.datetime.now().replace(second=0, microsecond=0)
            now += datetime.timedelta(seconds=seconds)
            if self.timelog.valid_time(now):
                entry = entry[delta_match.end():]
            else:
                now = None

        if not entry:
            return
        self.add_history(entry)
        self.timelog.append(entry, now)
        if self.chronological:
            self.delete_footer()
            self.write_item(self.timelog.window.last_entry())
            self.add_footer()
            self.scroll_to_end()
        else:
            self.populate_log()
        self.task_entry.set_text("")
        self.task_entry.grab_focus()
        self.tick(True)
        for watcher in self.entry_watchers:
            watcher(entry)

    def tick(self, force_update=False):
        """Tick every second."""
        if self.tasks.check_reload():
            self.set_up_task_list()
        now = datetime.datetime.now().replace(second=0, microsecond=0)
        if now == self.last_tick and not force_update:
            # Do not eat CPU unnecessarily
            return True
        self.last_tick = now
        last_time = self.timelog.window.last_time()
        if last_time is None:
            self.time_label.set_text(now.strftime("%H:%M"))
        else:
            self.time_label.set_text(format_duration(now - last_time))
            # Update "time left to work"
            if not self.lock:
                self.delete_footer()
                self.add_footer()
        return True


def main():
    """Run the program."""
    if len(sys.argv) > 1 and sys.argv[1] == '--sample-config':
        settings = Settings()
        settings.save("gtimelogrc.sample")
        print "Sample configuration file written to gtimelogrc.sample"
        return

    configdir = os.path.expanduser('~/.gtimelog')
    try:
        os.makedirs(configdir) # create it if it doesn't exist
    except OSError:
        pass
    settings = Settings()
    settings_file = os.path.join(configdir, 'gtimelogrc')
    if not os.path.exists(settings_file):
        settings.save(settings_file)
    else:
        settings.load(settings_file)
    timelog = TimeLog(os.path.join(configdir, 'timelog.txt'),
                      settings.virtual_midnight)
    if settings.task_list_url:
        tasks = RemoteTaskList(settings.task_list_url,
                               os.path.join(configdir, 'remote-tasks.txt'))
    else:
        tasks = TaskList(os.path.join(configdir, 'tasks.txt'))
    main_window = MainWindow(timelog, settings, tasks)
    if settings.show_tray_icon:
        if settings.prefer_old_tray_icon:
            icons = [OldTrayIcon, SimpleStatusIcon]
        else:
            icons = [SimpleStatusIcon, OldTrayIcon]
        for icon_class in icons:
            tray_icon = icon_class(main_window)
            if tray_icon.available():
                break # found one that works
    try:
        gtk.main()
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    main()
