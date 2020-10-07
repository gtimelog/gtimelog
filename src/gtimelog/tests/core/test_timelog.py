import unittest
from datetime import datetime, time
from io import StringIO

from gtimelog.tests.core import make_time_window


def doctest_timewindow_repr():
    """Test for TimeWindow.__repr__

        >>> minimum = datetime(2013, 12, 3)
        >>> maximum = datetime(2013, 12, 4)
        >>> vm = time(2, 0)

        >>> make_time_window(minimum=minimum, maximum=maximum, vm=vm)
        <TimeWindow: 2013-12-03 00:00:00..2013-12-04 00:00:00>

    """


def doctest_timewindow_reread_no_file():
    """Test for TimeWindow.reread

        >>> window = make_time_window('/nosuchfile')

    There's no error.

        >>> len(window.items)
        0
        >>> window.last_time()

    """


def doctest_timewindow_reread_bad_timestamp():
    """Test for TimeWindow.reread

        >>> minimum = datetime(2013, 12, 4)
        >>> maximum = datetime(2013, 12, 5)
        >>> vm = time(2, 0)

        >>> sampledata = StringIO('''
        ... 2013-12-04 09:00: start **
        ... # hey: this is not a timestamp
        ... 2013-12-04 09:14: gtimelog: write some tests
        ... ''')

        >>> window = make_time_window(sampledata, minimum, maximum, vm)

    There's no error, the line with a bad timestamp is silently skipped.

        >>> len(window.items)
        2

    """


def doctest_timewindow_reread_bad_ordering():
    """Test for TimeWindow.reread

        >>> minimum = datetime(2013, 12, 4)
        >>> maximum = datetime(2013, 12, 5)

        >>> sampledata = StringIO('''
        ... 2013-12-04 09:00: start **
        ... 2013-12-04 09:14: gtimelog: write some tests
        ... 2013-12-04 09:10: gtimelog: whoops clock got all confused
        ... 2013-12-04 09:10: gtimelog: so this will need to be fixed
        ... ''')

        >>> window = make_time_window(sampledata, minimum, maximum)

    There's no error, the timestamps have been reordered, but note that
    order was preserved for events with the same timestamp

        >>> for t, e in window.items:
        ...     print("%s: %s" % (t.strftime('%H:%M'), e))
        09:00: start **
        09:10: gtimelog: whoops clock got all confused
        09:10: gtimelog: so this will need to be fixed
        09:14: gtimelog: write some tests

        >>> window.last_time()
        datetime.datetime(2013, 12, 4, 9, 14)

    """


def doctest_timewindow_count_days():
    """Test for TimeWindow.count_days

        >>> minimum = datetime(2013, 12, 2)
        >>> maximum = datetime(2013, 12, 9)
        >>> vm = time(2, 0)

        >>> sampledata = StringIO('''
        ... 2013-12-04 09:00: start **
        ... 2013-12-04 09:14: gtimelog: write some tests
        ... 2013-12-04 09:10: gtimelog: whoops clock got all confused
        ... 2013-12-04 09:10: gtimelog: so this will need to be fixed
        ...
        ... 2013-12-05 22:30: some fictional late night work **
        ... 2013-12-06 00:30: frobnicate the widgets
        ...
        ... 2013-12-08 09:00: work **
        ... 2013-12-08 09:01: and stuff
        ... ''')

        >>> window = make_time_window(sampledata, minimum, maximum, vm)
        >>> window.count_days()
        3

    """


def doctest_timewindow_last_entry():
    """Test for TimeWindow.last_entry

        >>> window = make_time_window()

    Case #1: no items

        >>> window.items = []
        >>> window.last_entry()

    Case #2: single item

        >>> window.items = [
        ...     (datetime(2013, 12, 4, 9, 0), 'started **'),
        ... ]
        >>> start, stop, duration, tags, entry = window.last_entry()
        >>> start == stop == datetime(2013, 12, 4, 9, 0)
        True
        >>> duration
        datetime.timedelta(0)
        >>> entry
        'started **'

    Case #3: single item at start of new day

        >>> window.items = [
        ...     (datetime(2013, 12, 3, 12, 0), 'stuff'),
        ...     (datetime(2013, 12, 4, 9, 0), 'started **'),
        ... ]
        >>> start, stop, duration, tags, entry = window.last_entry()
        >>> start == stop == datetime(2013, 12, 4, 9, 0)
        True
        >>> duration
        datetime.timedelta(0)
        >>> entry
        'started **'


    Case #4: several items

        >>> window.items = [
        ...     (datetime(2013, 12, 4, 9, 0), 'started **'),
        ...     (datetime(2013, 12, 4, 9, 31), 'gtimelog: tests'),
        ... ]
        >>> start, stop, duration, tags, entry = window.last_entry()
        >>> start
        datetime.datetime(2013, 12, 4, 9, 0)
        >>> stop
        datetime.datetime(2013, 12, 4, 9, 31)
        >>> duration
        datetime.timedelta(0, 1860)
        >>> entry
        'gtimelog: tests'

    """


def test_suite():
    return unittest.defaultTestLoader.loadTestsFromName(__name__)

