"""
Misc utils
"""
import datetime
import os
import re
import sys
from gettext import gettext as _

import gi


def require_version(namespace, version):
    try:
        gi.require_version(namespace, version)
    except ValueError:
        deb_package = "gir1.2-{namespace}-{version}".format(
            namespace=namespace.lower(), version=version)
        sys.exit("""Typelib files for {namespace}-{version} are not available.

If you're on Ubuntu or another Debian-like distribution, please install
them with

    sudo apt install {deb_package}
""".format(namespace=namespace, version=version, deb_package=deb_package))


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


def internationalized_format_duration(duration):
    """Format a datetime.timedelta with minute precision.

    The difference from format_duration() is that this
    one is internationalized.
    """
    h, m = divmod(as_minutes(duration), 60)
    return _('{0} h {1} min').format(h, m)


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
        min = int(dt[14:])
    except ValueError:
        raise ValueError('bad date time: %r' % dt)
    return datetime.datetime(year, month, day, hour, min)


def parse_time(t):
    """Parse a time instance from 'HH:MM' formatted string."""
    m = re.match(r'^(\d+):(\d+)$', t)
    if not m:
        raise ValueError('bad time: %r' % t)
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


def uniq(items):
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