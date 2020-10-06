import csv
import datetime
import socket
from hashlib import md5

from gtimelog.core.utils import as_minutes, as_hours


class Exports(object):
    """Exporting of events."""

    def __init__(self, window):
        self.window = window

    @staticmethod
    def _hash(start, stop, entry):
        return md5(("%s%s%s" % (start, stop, entry)).encode('UTF-8')).hexdigest()

    def icalendar(self, output):
        """Create an iCalendar file with activities."""
        output.write("BEGIN:VCALENDAR\n")
        output.write("PRODID:-//gtimelog.org/NONSGML GTimeLog//EN\n")
        output.write("VERSION:2.0\n")
        idhost = socket.getfqdn()
        dtstamp = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        for start, stop, duration, tags, entry in self.window.all_entries():
            output.write("BEGIN:VEVENT\n")
            output.write("UID:%s@%s\n" % (self._hash(start, stop, entry), idhost))
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
        writer = csv.writer(output)
        if title_row:
            writer.writerow(["task", "time (minutes)"])
        work, slack = self.window.grouped_entries()
        work = [(entry, as_minutes(duration))
                for start, entry, duration in work
                if duration]  # skip empty "arrival" entries
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
        # timelog must be chronological for this to be dependable

        d0 = datetime.timedelta(0)
        days = {}  # date -> [time_started, slacking, work]
        dmin = None
        start = None
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

        if dmin and start:
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
