import os
import re
import time
import datetime
from email.header import Header
from email.mime.text import MIMEText
from email.utils import parseaddr, formataddr
from operator import itemgetter

from gtimelog import __version__, DEBUG
from gtimelog.paths import CONTRIBUTORS_FILE


def mark_time(what=None, _prev=None):
    if _prev is None:
        _prev = [0, 0]
    if DEBUG:
        t = time.time()
        if what:
            print("{:.3f} ({:+.3f}) {}".format(t - _prev[1], t - _prev[0], what))
        else:
            print()
            _prev[1] = t
        _prev[0] = t


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
        raise ValueError('bad date time: %r' % dt)
    try:
        year = int(dt[:4])
        month = int(dt[5:7])
        day = int(dt[8:10])
        hour = int(dt[11:13])
        minimum = int(dt[14:])
    except ValueError:
        raise ValueError('bad date time: %r' % dt)
    return datetime.datetime(year, month, day, hour, minimum)


def parse_time(t):
    """Parse a time instance from 'HH:MM' formatted string."""
    m = re.match(r'^(\d+):(\d+)$', t)
    if not m:
        raise ValueError('bad time: %r' % t)
    hour, minute = map(int, m.groups())
    return datetime.time(hour, minute)


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


def linear_unicity(items):
    """Return list with consecutive duplicates removed."""
    result = items[:1]
    for item in items[1:]:
        if item != result[-1]:
            result.append(item)
    return result


def get_mtime(filename):
    """Return the modification time of a file, if it exists.

    Returns None if the file doesn't exist.
    """
    # Accept any file-like object instead of a filename (for the benefit of
    # unit tests).
    if hasattr(filename, 'read'):
        return None
    try:
        return os.stat(filename).st_mtime
    except OSError:
        return None


def isascii(s):
    return all(0 <= ord(c) <= 127 for c in s)


def address_header(name_and_address):
    if isascii(name_and_address):
        return name_and_address
    name, addr = parseaddr(name_and_address)
    name = str(Header(name, 'UTF-8'))
    return formataddr((name, addr))


def subject_header(header):
    if isascii(header):
        return header
    return Header(header, 'UTF-8')


def prepare_message(sender, recipient, subject, body):
    if isascii(body):
        msg = MIMEText(body)
    else:
        msg = MIMEText(body, _charset="UTF-8")
    if sender:
        msg["From"] = address_header(sender)
    msg["To"] = address_header(recipient)
    msg["Subject"] = subject_header(subject)
    msg["User-Agent"] = "gtimelog/{}".format(__version__)
    return msg


def report_categories(output, categories):
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


def parse_timelog(f):
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


def get_contributors():
    contributors = []
    with open(CONTRIBUTORS_FILE, encoding='UTF-8') as f:
        for line in f:
            if line.startswith('- '):
                contributors.append(line[2:].strip())
    return sorted(contributors)
