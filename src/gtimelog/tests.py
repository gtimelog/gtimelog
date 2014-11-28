"""Tests for gtimelog"""

import datetime
import doctest
import unittest
import os
import tempfile
import shutil
from pprint import pprint

try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO


def doctest_as_hours():
    """Tests for as_hours

        >>> from gtimelog.timelog import as_hours
        >>> from datetime import timedelta
        >>> as_hours(timedelta(0))
        0.0
        >>> as_hours(timedelta(minutes=30))
        0.5
        >>> as_hours(timedelta(minutes=60))
        1.0
        >>> as_hours(timedelta(days=2))
        48.0

    """


def doctest_format_duration():
    """Tests for format_duration.

        >>> from gtimelog.timelog import format_duration
        >>> from datetime import timedelta
        >>> format_duration(timedelta(0))
        '0 h 0 min'
        >>> format_duration(timedelta(minutes=1))
        '0 h 1 min'
        >>> format_duration(timedelta(minutes=60))
        '1 h 0 min'

    """


def doctest_format_short():
    """Tests for format_duration_short.

        >>> from gtimelog.timelog import format_duration_short
        >>> from datetime import timedelta
        >>> format_duration_short(timedelta(0))
        '0:00'
        >>> format_duration_short(timedelta(minutes=1))
        '0:01'
        >>> format_duration_short(timedelta(minutes=59))
        '0:59'
        >>> format_duration_short(timedelta(minutes=60))
        '1:00'
        >>> format_duration_short(timedelta(days=1, hours=2, minutes=3))
        '26:03'

    """


def doctest_format_duration_long():
    """Tests for format_duration_long.

        >>> from gtimelog.timelog import format_duration_long
        >>> from datetime import timedelta
        >>> format_duration_long(timedelta(0))
        '0 min'
        >>> format_duration_long(timedelta(minutes=1))
        '1 min'
        >>> format_duration_long(timedelta(minutes=60))
        '1 hour'
        >>> format_duration_long(timedelta(minutes=65))
        '1 hour 5 min'
        >>> format_duration_long(timedelta(hours=2))
        '2 hours'
        >>> format_duration_long(timedelta(hours=2, minutes=1))
        '2 hours 1 min'

    """


def doctest_parse_datetime():
    """Tests for parse_datetime

        >>> from gtimelog.timelog import parse_datetime
        >>> parse_datetime('2005-02-03 02:13')
        datetime.datetime(2005, 2, 3, 2, 13)
        >>> parse_datetime('xyzzy')
        Traceback (most recent call last):
          ...
        ValueError: ('bad date time: ', 'xyzzy')

    """


def doctest_parse_time():
    """Tests for parse_time

        >>> from gtimelog.timelog import parse_time
        >>> parse_time('02:13')
        datetime.time(2, 13)
        >>> parse_time('xyzzy')
        Traceback (most recent call last):
          ...
        ValueError: ('bad time: ', 'xyzzy')

    """


def doctest_virtual_day():
    """Tests for virtual_day

        >>> from datetime import datetime, time
        >>> from gtimelog.timelog import virtual_day

    Virtual midnight

        >>> vm = time(2, 0)

    The tests themselves:

        >>> virtual_day(datetime(2005, 2, 3, 1, 15), vm)
        datetime.date(2005, 2, 2)
        >>> virtual_day(datetime(2005, 2, 3, 1, 59), vm)
        datetime.date(2005, 2, 2)
        >>> virtual_day(datetime(2005, 2, 3, 2, 0), vm)
        datetime.date(2005, 2, 3)
        >>> virtual_day(datetime(2005, 2, 3, 12, 0), vm)
        datetime.date(2005, 2, 3)
        >>> virtual_day(datetime(2005, 2, 3, 23, 59), vm)
        datetime.date(2005, 2, 3)

    """


def doctest_different_days():
    """Tests for different_days

        >>> from datetime import datetime, time
        >>> from gtimelog.timelog import different_days

    Virtual midnight

        >>> vm = time(2, 0)

    The tests themselves:

        >>> different_days(datetime(2005, 2, 3, 1, 15),
        ...                datetime(2005, 2, 3, 2, 15), vm)
        True
        >>> different_days(datetime(2005, 2, 3, 11, 15),
        ...                datetime(2005, 2, 3, 12, 15), vm)
        False

    """


def doctest_first_of_month():
    """Tests for first_of_month

        >>> from gtimelog.timelog import first_of_month
        >>> from datetime import date, timedelta

        >>> first_of_month(date(2007, 1, 1))
        datetime.date(2007, 1, 1)

        >>> first_of_month(date(2007, 1, 7))
        datetime.date(2007, 1, 1)

        >>> first_of_month(date(2007, 1, 31))
        datetime.date(2007, 1, 1)

        >>> first_of_month(date(2007, 2, 1))
        datetime.date(2007, 2, 1)

        >>> first_of_month(date(2007, 2, 28))
        datetime.date(2007, 2, 1)

        >>> first_of_month(date(2007, 3, 1))
        datetime.date(2007, 3, 1)

    Why not test extensively?

        >>> d = date(2000, 1, 1)
        >>> while d < date(2005, 1, 1):
        ...     f = first_of_month(d)
        ...     if (f.year, f.month, f.day) != (d.year, d.month, 1):
        ...         print("WRONG: first_of_month(%r) returned %r" % (d, f))
        ...     d += timedelta(1)

    """


def doctest_next_month():
    """Tests for next_month

        >>> from gtimelog.timelog import next_month
        >>> from datetime import date, timedelta

        >>> next_month(date(2007, 1, 1))
        datetime.date(2007, 2, 1)

        >>> next_month(date(2007, 1, 7))
        datetime.date(2007, 2, 1)

        >>> next_month(date(2007, 1, 31))
        datetime.date(2007, 2, 1)

        >>> next_month(date(2007, 2, 1))
        datetime.date(2007, 3, 1)

        >>> next_month(date(2007, 2, 28))
        datetime.date(2007, 3, 1)

        >>> next_month(date(2007, 3, 1))
        datetime.date(2007, 4, 1)

    Why not test extensively?

        >>> d = date(2000, 1, 1)
        >>> while d < date(2005, 1, 1):
        ...     f = next_month(d)
        ...     prev = f - timedelta(1)
        ...     if f.day != 1 or (prev.year, prev.month) != (d.year, d.month):
        ...         print("WRONG: next_month(%r) returned %r" % (d, f))
        ...     d += timedelta(1)

    """


def doctest_uniq():
    """Tests for uniq

        >>> from gtimelog.timelog import uniq
        >>> uniq(['a', 'b', 'b', 'c', 'd', 'b', 'd'])
        ['a', 'b', 'c', 'd', 'b', 'd']
        >>> uniq(['a'])
        ['a']
        >>> uniq([])
        []

    """


def doctest_TimeWindow_reread_no_file():
    """Test for TimeWindow.reread

        >>> from datetime import datetime, time
        >>> min = datetime(2013, 12, 3)
        >>> max = datetime(2013, 12, 4)
        >>> vm = time(2, 0)

        >>> from gtimelog.timelog import TimeWindow
        >>> window = TimeWindow('/nosuchfile', min, max, vm)

    There's no error.

        >>> len(window.items)
        0
        >>> window.last_time()

    """


def doctest_TimeWindow_reread_bad_timestamp():
    """Test for TimeWindow.reread

        >>> from datetime import datetime, time
        >>> min = datetime(2013, 12, 4)
        >>> max = datetime(2013, 12, 5)
        >>> vm = time(2, 0)

        >>> sampledata = StringIO('''
        ... 2013-12-04 09:00: start **
        ... # hey: this is not a timestamp
        ... 2013-12-04 09:14: gtimelog: write some tests
        ... ''')

        >>> from gtimelog.timelog import TimeWindow
        >>> window = TimeWindow(sampledata, min, max, vm)

    There's no error, the line with a bad timestamp is silently skipped.

        >>> len(window.items)
        2

    """


def doctest_TimeWindow_reread_bad_ordering():
    """Test for TimeWindow.reread

        >>> from datetime import datetime, time
        >>> min = datetime(2013, 12, 4)
        >>> max = datetime(2013, 12, 5)
        >>> vm = time(2, 0)

        >>> sampledata = StringIO('''
        ... 2013-12-04 09:00: start **
        ... 2013-12-04 09:14: gtimelog: write some tests
        ... 2013-12-04 09:10: gtimelog: whoops clock got all confused
        ... 2013-12-04 09:10: gtimelog: so this will need to be fixed
        ... ''')

        >>> from gtimelog.timelog import TimeWindow
        >>> window = TimeWindow(sampledata, min, max, vm)

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


def doctest_TimeWindow_reread_callbacks():
    """Test for TimeWindow.reread

        >>> from datetime import datetime, time
        >>> min = datetime(2013, 12, 4)
        >>> max = datetime(2013, 12, 5)
        >>> vm = time(2, 0)

        >>> sampledata = StringIO('''
        ... 2013-12-03 09:00: stuff **
        ... 2013-12-04 09:00: start **
        ... 2013-12-04 09:14: gtimelog: write some tests
        ... 2013-12-06 09:00: future **
        ... ''')

        >>> l = []

        >>> from gtimelog.timelog import TimeWindow
        >>> window = TimeWindow(sampledata, min, max, vm, callback=l.append)

    The callback is invoked with all the entries (not just those in the
    selected time window).  We use it to populate history completion.

        >>> l
        ['stuff **', 'start **', 'gtimelog: write some tests', 'future **']

    """


def doctest_TimeWindow_count_days():
    """Test for TimeWindow.count_days

        >>> from datetime import datetime, time
        >>> min = datetime(2013, 12, 2)
        >>> max = datetime(2013, 12, 9)
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

        >>> from gtimelog.timelog import TimeWindow
        >>> window = TimeWindow(sampledata, min, max, vm)
        >>> window.count_days()
        3

    """


def doctest_TimeWindow_last_entry():
    """Test for TimeWindow.last_entry

        >>> from datetime import datetime, time
        >>> vm = time(2, 0)

        >>> from gtimelog.timelog import TimeWindow
        >>> window = TimeWindow(StringIO(), None, None, vm)

    Case #1: no items

        >>> window.items = []
        >>> window.last_entry()

    Case #2: single item

        >>> window.items = [
        ...     (datetime(2013, 12, 4, 9, 0), 'started **'),
        ... ]
        >>> start, stop, duration, entry = window.last_entry()
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
        >>> start, stop, duration, entry = window.last_entry()
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
        >>> start, stop, duration, entry = window.last_entry()
        >>> start
        datetime.datetime(2013, 12, 4, 9, 0)
        >>> stop
        datetime.datetime(2013, 12, 4, 9, 31)
        >>> duration
        datetime.timedelta(0, 1860)
        >>> entry
        'gtimelog: tests'

    """


def doctest_TimeWindow_to_csv_complete():
    r"""Tests for TimeWindow.to_csv_complete

        >>> from datetime import datetime, time
        >>> min = datetime(2008, 6, 1)
        >>> max = datetime(2008, 7, 1)
        >>> vm = time(2, 0)

        >>> sampledata = StringIO('''
        ... 2008-06-03 12:45: start
        ... 2008-06-03 13:00: something
        ... 2008-06-03 14:45: something else
        ... 2008-06-03 15:45: etc
        ... 2008-06-05 12:45: start
        ... 2008-06-05 13:15: something
        ... 2008-06-05 14:15: rest **
        ... 2008-06-05 16:15: let's not mention this ever again ***
        ... ''')

        >>> from gtimelog.timelog import TimeWindow
        >>> window = TimeWindow(sampledata, min, max, vm)

        >>> import sys
        >>> window.to_csv_complete(sys.stdout)
        task,time (minutes)
        etc,60
        something,45
        something else,105

    """


def doctest_TimeWindow_to_csv_daily():
    r"""Tests for TimeWindow.to_csv_daily

        >>> from datetime import datetime, time
        >>> min = datetime(2008, 6, 1)
        >>> max = datetime(2008, 7, 1)
        >>> vm = time(2, 0)

        >>> sampledata = StringIO('''
        ... 2008-06-03 12:45: start
        ... 2008-06-03 13:00: something
        ... 2008-06-03 14:45: something else
        ... 2008-06-03 15:45: etc
        ... 2008-06-05 12:45: start
        ... 2008-06-05 13:15: something
        ... 2008-06-05 14:15: rest **
        ... ''')

        >>> from gtimelog.timelog import TimeWindow
        >>> window = TimeWindow(sampledata, min, max, vm)

        >>> import sys
        >>> window.to_csv_daily(sys.stdout)
        date,day-start (hours),slacking (hours),work (hours)
        2008-06-03,12.75,0.0,3.0
        2008-06-04,0.0,0.0,0.0
        2008-06-05,12.75,1.0,0.5

    """


def doctest_Reports_weekly_report_categorized():
    r"""Tests for Reports.weekly_report_categorized

        >>> import sys

        >>> from datetime import datetime, time
        >>> from gtimelog.timelog import TimeWindow, Reports

        >>> vm = time(2, 0)
        >>> min = datetime(2010, 1, 25)
        >>> max = datetime(2010, 1, 31)

        >>> window = TimeWindow(StringIO(), min, max, vm)
        >>> reports = Reports(window)
        >>> reports.weekly_report_categorized(sys.stdout, 'foo@bar.com',
        ...                                   'Bob Jones')
        To: foo@bar.com
        Subject: Weekly report for Bob Jones (week 04)
        <BLANKLINE>
        No work done this week.

        >>> fh = StringIO('\n'.join([
        ...    '2010-01-30 09:00: start',
        ...    '2010-01-30 09:23: Bing: stuff',
        ...    '2010-01-30 12:54: Bong: other stuff',
        ...    '2010-01-30 13:32: lunch **',
        ...    '2010-01-30 23:46: misc',
        ...    '']))

        >>> window = TimeWindow(fh, min, max, vm)
        >>> reports = Reports(window)
        >>> reports.weekly_report_categorized(sys.stdout, 'foo@bar.com',
        ...                                   'Bob Jones')
        To: foo@bar.com
        Subject: Weekly report for Bob Jones (week 04)
        <BLANKLINE>
                                                                        time
        Bing:
        <BLANKLINE>
          Stuff                                                           0:23
        ----------------------------------------------------------------------
                                                                          0:23
        <BLANKLINE>
        Bong:
        <BLANKLINE>
          Other stuff                                                     3:31
        ----------------------------------------------------------------------
                                                                          3:31
        <BLANKLINE>
        No category:
        <BLANKLINE>
          Misc                                                           10:14
        ----------------------------------------------------------------------
                                                                         10:14
        <BLANKLINE>
        Total work done this week: 14:08
        <BLANKLINE>
        Categories by time spent:
          No category     10:14
          Bong             3:31
          Bing             0:23

    """


def doctest_Reports_monthly_report_categorized():
    r"""Tests for Reports.monthly_report_categorized

        >>> import sys

        >>> from datetime import datetime, time
        >>> from gtimelog.timelog import TimeWindow, Reports

        >>> vm = time(2, 0)
        >>> min = datetime(2010, 1, 25)
        >>> max = datetime(2010, 1, 31)

        >>> window = TimeWindow(StringIO(), min, max, vm)
        >>> reports = Reports(window)
        >>> reports.monthly_report_categorized(sys.stdout, 'foo@bar.com',
        ...                                   'Bob Jones')
        To: foo@bar.com
        Subject: Monthly report for Bob Jones (2010/01)
        <BLANKLINE>
        No work done this month.

        >>> fh = StringIO('\n'.join([
        ...    '2010-01-30 09:00: start',
        ...    '2010-01-30 09:23: Bing: stuff',
        ...    '2010-01-30 12:54: Bong: other stuff',
        ...    '2010-01-30 13:32: lunch **',
        ...    '2010-01-30 23:46: misc',
        ...    '']))

        >>> window = TimeWindow(fh, min, max, vm)
        >>> reports = Reports(window)
        >>> reports.monthly_report_categorized(sys.stdout, 'foo@bar.com',
        ...                                   'Bob Jones')
        To: foo@bar.com
        Subject: Monthly report for Bob Jones (2010/01)
        <BLANKLINE>
                                                                          time
        Bing:
          Stuff                                                           0:23
        ----------------------------------------------------------------------
                                                                          0:23
        <BLANKLINE>
        Bong:
          Other stuff                                                     3:31
        ----------------------------------------------------------------------
                                                                          3:31
        <BLANKLINE>
        No category:
          Misc                                                           10:14
        ----------------------------------------------------------------------
                                                                         10:14
        <BLANKLINE>
        Total work done this month: 14:08
        <BLANKLINE>
        Categories by time spent:
          No category     10:14
          Bong             3:31
          Bing             0:23

    """


def doctest_Reports_report_categories():
    r"""Tests for Reports._report_categories

        >>> import sys

        >>> from datetime import datetime, time, timedelta
        >>> from gtimelog.timelog import TimeWindow, Reports

        >>> vm = time(2, 0)
        >>> min = datetime(2010, 1, 25)
        >>> max = datetime(2010, 1, 31)

        >>> categories = {
        ...    'Bing': timedelta(2),
        ...    None: timedelta(1)}

        >>> window = TimeWindow(StringIO(), min, max, vm)
        >>> reports = Reports(window)
        >>> reports._report_categories(sys.stdout, categories)
        <BLANKLINE>
        By category:
        <BLANKLINE>
        Bing                                                            48 hours
        (none)                                                          24 hours
        <BLANKLINE>

    """


def doctest_Reports_daily_report():
    r"""Tests for Reports.daily_report

        >>> import sys

        >>> from datetime import datetime, time
        >>> from gtimelog.timelog import TimeWindow, Reports

        >>> vm = time(2, 0)
        >>> min = datetime(2010, 1, 30)
        >>> max = datetime(2010, 1, 31)

        >>> window = TimeWindow(StringIO(), min, max, vm)
        >>> reports = Reports(window)
        >>> reports.daily_report(sys.stdout, 'foo@bar.com', 'Bob Jones')
        To: foo@bar.com
        Subject: 2010-01-30 report for Bob Jones (Sat, week 04)
        <BLANKLINE>
        No work done today.

        >>> fh = StringIO('\n'.join([
        ...    '2010-01-30 09:00: start',
        ...    '2010-01-30 09:23: Bing: stuff',
        ...    '2010-01-30 12:54: Bong: other stuff',
        ...    '2010-01-30 13:32: lunch **',
        ...    '2010-01-30 15:46: misc',
        ...    '']))

        >>> window = TimeWindow(fh, min, max, vm)
        >>> reports = Reports(window)
        >>> reports.daily_report(sys.stdout, 'foo@bar.com', 'Bob Jones')
        To: foo@bar.com
        Subject: 2010-01-30 report for Bob Jones (Sat, week 04)
        <BLANKLINE>
        Start at 09:00
        <BLANKLINE>
        Bing: stuff                                                     23 min
        Bong: other stuff                                               3 hours 31 min
        Misc                                                            2 hours 14 min
        <BLANKLINE>
        Total work done: 6 hours 8 min
        <BLANKLINE>
        By category:
        <BLANKLINE>
        Bing                                                            23 min
        Bong                                                            3 hours 31 min
        (none)                                                          2 hours 14 min
        <BLANKLINE>
        Slacking:
        <BLANKLINE>
        Lunch **                                                        38 min
        <BLANKLINE>
        Time spent slacking: 38 min

    """


def doctest_Reports_weekly_report_plain():
    r"""Tests for Reports.weekly_report_plain

        >>> import sys

        >>> from datetime import datetime, time
        >>> from gtimelog.timelog import TimeWindow, Reports

        >>> vm = time(2, 0)
        >>> min = datetime(2010, 1, 25)
        >>> max = datetime(2010, 1, 31)

        >>> window = TimeWindow(StringIO(), min, max, vm)
        >>> reports = Reports(window)
        >>> reports.weekly_report_plain(sys.stdout, 'foo@bar.com', 'Bob Jones')
        To: foo@bar.com
        Subject: Weekly report for Bob Jones (week 04)
        <BLANKLINE>
        No work done this week.

        >>> fh = StringIO('\n'.join([
        ...    '2010-01-30 09:00: start',
        ...    '2010-01-30 09:23: Bing: stuff',
        ...    '2010-01-30 12:54: Bong: other stuff',
        ...    '2010-01-30 13:32: lunch **',
        ...    '2010-01-30 15:46: misc',
        ...    '']))

        >>> window = TimeWindow(fh, min, max, vm)
        >>> reports = Reports(window)
        >>> reports.weekly_report_plain(sys.stdout, 'foo@bar.com', 'Bob Jones')
        To: foo@bar.com
        Subject: Weekly report for Bob Jones (week 04)
        <BLANKLINE>
                                                                        time
        Bing: stuff                                                     23 min
        Bong: other stuff                                               3 hours 31 min
        Misc                                                            2 hours 14 min
        <BLANKLINE>
        Total work done this week: 6 hours 8 min
        <BLANKLINE>
        By category:
        <BLANKLINE>
        Bing                                                            23 min
        Bong                                                            3 hours 31 min
        (none)                                                          2 hours 14 min
        <BLANKLINE>

    """


def doctest_Reports_monthly_report_plain():
    r"""Tests for Reports.monthly_report_plain

        >>> import sys

        >>> from datetime import datetime, time
        >>> from gtimelog.timelog import TimeWindow, Reports

        >>> vm = time(2, 0)
        >>> min = datetime(2007, 9, 1)
        >>> max = datetime(2007, 10, 1)

        >>> window = TimeWindow(StringIO(), min, max, vm)
        >>> reports = Reports(window)
        >>> reports.monthly_report_plain(sys.stdout, 'foo@bar.com', 'Bob Jones')
        To: foo@bar.com
        Subject: Monthly report for Bob Jones (2007/09)
        <BLANKLINE>
        No work done this month.

        >>> fh = StringIO('\n'.join([
        ...    '2007-09-30 09:00: start',
        ...    '2007-09-30 09:23: Bing: stuff',
        ...    '2007-09-30 12:54: Bong: other stuff',
        ...    '2007-09-30 13:32: lunch **',
        ...    '2007-09-30 15:46: misc',
        ...    '']))

        >>> window = TimeWindow(fh, min, max, vm)
        >>> reports = Reports(window)
        >>> reports.monthly_report_plain(sys.stdout, 'foo@bar.com', 'Bob Jones')
        To: foo@bar.com
        Subject: Monthly report for Bob Jones (2007/09)
        <BLANKLINE>
                                                                       time
        Bing: stuff                                                     23 min
        Bong: other stuff                                               3 hours 31 min
        Misc                                                            2 hours 14 min
        <BLANKLINE>
        Total work done this month: 6 hours 8 min
        <BLANKLINE>
        By category:
        <BLANKLINE>
        Bing                                                            23 min
        Bong                                                            3 hours 31 min
        (none)                                                          2 hours 14 min
        <BLANKLINE>

    """


def doctest_Reports_custom_range_report_categorized():
    r"""Tests for Reports.custom_range_report_categorized

        >>> import sys

        >>> from datetime import datetime, time
        >>> from gtimelog.timelog import TimeWindow, Reports

        >>> vm = time(2, 0)
        >>> min = datetime(2010, 1, 25)
        >>> max = datetime(2010, 2, 1)

        >>> window = TimeWindow(StringIO(), min, max, vm)
        >>> reports = Reports(window)
        >>> reports.custom_range_report_categorized(sys.stdout, 'foo@bar.com',
        ...                                         'Bob Jones')
        To: foo@bar.com
        Subject: Custom date range report for Bob Jones (2010-01-25 - 2010-01-31)
        <BLANKLINE>
        No work done this custom range.

        >>> fh = StringIO('\n'.join([
        ...    '2010-01-20 09:00: arrived',
        ...    '2010-01-20 09:30: asdf',
        ...    '2010-01-20 10:00: Bar: Foo',
        ...    ''
        ...    '2010-01-30 09:00: arrived',
        ...    '2010-01-30 09:23: Bing: stuff',
        ...    '2010-01-30 12:54: Bong: other stuff',
        ...    '2010-01-30 13:32: lunch **',
        ...    '2010-01-30 23:46: misc',
        ...    '']))

        >>> window = TimeWindow(fh, min, max, vm)
        >>> reports = Reports(window)
        >>> reports.custom_range_report_categorized(sys.stdout, 'foo@bar.com',
        ...                                         'Bob Jones')
        To: foo@bar.com
        Subject: Custom date range report for Bob Jones (2010-01-25 - 2010-01-31)
        <BLANKLINE>
                                                                          time
        Bing:
          Stuff                                                           0:23
        ----------------------------------------------------------------------
                                                                          0:23
        <BLANKLINE>
        Bong:
          Other stuff                                                     3:31
        ----------------------------------------------------------------------
                                                                          3:31
        <BLANKLINE>
        No category:
          Misc                                                           10:14
        ----------------------------------------------------------------------
                                                                         10:14
        <BLANKLINE>
        Total work done this custom range: 14:08
        <BLANKLINE>
        Categories by time spent:
          No category     10:14
          Bong             3:31
          Bing             0:23

    """


def doctest_TaskList_missing_file():
    """Test for TaskList

        >>> from gtimelog.timelog import TaskList
        >>> tasklist = TaskList('/nosuchfile')
        >>> tasklist.check_reload()
        False
        >>> tasklist.reload()

    """


def doctest_TaskList_real_file():
    r"""Test for TaskList

        >>> import time
        >>> tempdir = tempfile.mkdtemp(prefix='gtimelog-test-')
        >>> taskfile = os.path.join(tempdir, 'tasks.txt')
        >>> with open(taskfile, 'w') as f:
        ...     _ = f.write('\n'.join([
        ...         '# comments are skipped',
        ...         'some task',
        ...         'other task',
        ...         'project: do it',
        ...         'project: fix bugs',
        ...         'misc: paperwork',
        ...         ]) + '\n')
        >>> one_second_ago = time.time() - 2
        >>> os.utime(taskfile, (one_second_ago, one_second_ago))

        >>> from gtimelog.timelog import TaskList
        >>> tasklist = TaskList(taskfile)
        >>> pprint(tasklist.groups)
        [('Other', ['some task', 'other task']),
         ('misc', ['paperwork']),
         ('project', ['do it', 'fix bugs'])]

        >>> tasklist.check_reload()
        False

        >>> with open(taskfile, 'w') as f:
        ...     _ = f.write('new tasks\n')

        >>> tasklist.check_reload()
        True

        >>> pprint(tasklist.groups)
        [('Other', ['new tasks'])]

        >>> shutil.rmtree(tempdir)

    """


class TestSettings(unittest.TestCase):

    def setUp(self):
        from gtimelog.settings import Settings
        self.settings = Settings()
        self.real_isdir = os.path.isdir
        self.tempdir = None
        self.old_home = os.environ.get('HOME')
        self.old_gtimelog_home = os.environ.get('GTIMELOG_HOME')
        self.old_xdg_config_home = os.environ.get('XDG_CONFIG_HOME')
        self.old_xdg_data_home = os.environ.get('XDG_DATA_HOME')
        os.environ['HOME'] = os.path.normpath('/tmp/home')
        os.environ.pop('GTIMELOG_HOME', None)
        os.environ.pop('XDG_CONFIG_HOME', None)
        os.environ.pop('XDG_DATA_HOME', None)

    def tearDown(self):
        os.path.isdir = self.real_isdir
        if self.tempdir:
            shutil.rmtree(self.tempdir)
        self.restore_env('HOME', self.old_home)
        self.restore_env('GTIMELOG_HOME', self.old_gtimelog_home)
        self.restore_env('XDG_CONFIG_HOME', self.old_xdg_config_home)
        self.restore_env('XDG_DATA_HOME', self.old_xdg_data_home)

    def restore_env(self, envvar, value):
        if value is not None:
            os.environ[envvar] = value
        else:
            os.environ.pop(envvar, None)

    def mkdtemp(self):
        if self.tempdir is None:
            self.tempdir = tempfile.mkdtemp(prefix='gtimelog-test-')
        return self.tempdir

    def test_get_config_dir_1(self):
        # Case 1: GTIMELOG_HOME is present in the environment
        os.environ['GTIMELOG_HOME'] = os.path.normpath('~/.gt')
        self.assertEqual(self.settings.get_config_dir(),
                         os.path.normpath('/tmp/home/.gt'))

    def test_get_config_dir_2(self):
        # Case 2: ~/.gtimelog exists
        os.path.isdir = lambda dir: True
        self.assertEqual(self.settings.get_config_dir(),
                         os.path.normpath('/tmp/home/.gtimelog'))

    def test_get_config_dir_3(self):
        # Case 3: ~/.gtimelog does not exist, so we use XDG
        os.path.isdir = lambda dir: False
        self.assertEqual(self.settings.get_config_dir(),
                         os.path.normpath('/tmp/home/.config/gtimelog'))

    def test_get_config_dir_4(self):
        # Case 4: XDG_CONFIG_HOME is present in the environment
        os.environ['XDG_CONFIG_HOME'] = os.path.normpath('~/.conf')
        self.assertEqual(self.settings.get_config_dir(),
                         os.path.normpath('/tmp/home/.conf/gtimelog'))

    def test_get_data_dir_1(self):
        # Case 1: GTIMELOG_HOME is present in the environment
        os.environ['GTIMELOG_HOME'] = os.path.normpath('~/.gt')
        self.assertEqual(self.settings.get_data_dir(),
                         os.path.normpath('/tmp/home/.gt'))

    def test_get_data_dir_2(self):
        # Case 2: ~/.gtimelog exists
        os.path.isdir = lambda dir: True
        self.assertEqual(self.settings.get_data_dir(),
                         os.path.normpath('/tmp/home/.gtimelog'))

    def test_get_data_dir_3(self):
        # Case 3: ~/.gtimelog does not exist, so we use XDG
        os.path.isdir = lambda dir: False
        self.assertEqual(self.settings.get_data_dir(),
                         os.path.normpath('/tmp/home/.local/share/gtimelog'))

    def test_get_data_dir_4(self):
        # Case 4: XDG_CONFIG_HOME is present in the environment
        os.environ['XDG_DATA_HOME'] = os.path.normpath('~/.data')
        self.assertEqual(self.settings.get_data_dir(),
                         os.path.normpath('/tmp/home/.data/gtimelog'))

    def test_get_config_file(self):
        self.settings.get_config_dir = lambda: os.path.normpath('~/.config/gtimelog')
        self.assertEqual(self.settings.get_config_file(),
                         os.path.normpath('~/.config/gtimelog/gtimelogrc'))

    def test_get_timelog_file(self):
        self.settings.get_data_dir = lambda: os.path.normpath('~/.local/share/gtimelog')
        self.assertEqual(self.settings.get_timelog_file(),
                         os.path.normpath('~/.local/share/gtimelog/timelog.txt'))

    def test_load(self):
        self.settings.load('/dev/null')

    def test_save(self):
        tempdir = self.mkdtemp()
        self.settings.save(os.path.join(tempdir, 'config'))


def additional_tests(): # for setup.py
    return doctest.DocTestSuite(optionflags=doctest.NORMALIZE_WHITESPACE)


def test_suite():
    return unittest.TestSuite([
        unittest.defaultTestLoader.loadTestsFromName(__name__),
        additional_tests(),
    ])


def main():
    unittest.TextTestRunner().run(test_suite())


if __name__ == '__main__':
    main()
