"""Tests for gtimelog.timelog"""

import datetime
import doctest
import os
import re
import shutil
import sys
import tempfile
import textwrap
import time
import unittest
from io import StringIO
from unittest import mock

import freezegun

from gtimelog.timelog import (
    Exports,
    ReportRecord,
    Reports,
    TaskList,
    TimeCollection,
    TimeLog,
)


class Checker(doctest.OutputChecker):
    """Doctest output checker that can deal with unicode literals."""

    def check_output(self, want, got, optionflags):
        # u'...' -> '...'; u"..." -> "..."
        got = re.sub(r'''\bu('[^']*'|"[^"]*")''', r'\1', got)
        # Python 3.7: datetime.timedelta(seconds=1860) ->
        # Python < 3.7: datetime.timedelta(0, 1860)
        got = re.sub(r'datetime[.]timedelta[(]seconds=(\d+)[)]',
                     r'datetime.timedelta(0, \1)', got)
        return doctest.OutputChecker.check_output(self, want, got, optionflags)


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
        ValueError: bad date time: 'xyzzy'
        >>> parse_datetime('YYYY-MM-DD HH:MM')
        Traceback (most recent call last):
          ...
        ValueError: bad date time: 'YYYY-MM-DD HH:MM'

    """


def doctest_parse_time():
    """Tests for parse_time

        >>> from gtimelog.timelog import parse_time
        >>> parse_time('02:13')
        datetime.time(2, 13)
        >>> parse_time('xyzzy')
        Traceback (most recent call last):
          ...
        ValueError: bad time: 'xyzzy'

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


def doctest_prev_month():
    """Tests for prev_month

        >>> from gtimelog.timelog import prev_month
        >>> from datetime import date, timedelta

        >>> prev_month(date(2007, 3, 1))
        datetime.date(2007, 2, 1)

        >>> prev_month(date(2007, 3, 7))
        datetime.date(2007, 2, 1)

        >>> prev_month(date(2007, 3, 31))
        datetime.date(2007, 2, 1)

        >>> prev_month(date(2007, 4, 1))
        datetime.date(2007, 3, 1)

        >>> prev_month(date(2007, 2, 28))
        datetime.date(2007, 1, 1)

        >>> prev_month(date(2007, 4, 1))
        datetime.date(2007, 3, 1)

    Why not test extensively?

        >>> d = date(2000, 1, 1)
        >>> while d < date(2005, 1, 1):
        ...     f = prev_month(d)
        ...     next = f + timedelta(31)
        ...     if f.day != 1 or (next.year, next.month) != (d.year, d.month):
        ...         print("WRONG: prev_month(%r) returned %r" % (d, f))
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


def make_time_window(file=None, min=None, max=None, vm=datetime.time(2)):
    if file is None:
        file = StringIO()
    return TimeLog(file, vm).window_for(min, max)


def doctest_TimeWindow_repr():
    """Test for TimeWindow.__repr__

        >>> from datetime import datetime, time
        >>> min = datetime(2013, 12, 3)
        >>> max = datetime(2013, 12, 4)
        >>> vm = time(2, 0)

        >>> make_time_window(min=min, max=max, vm=vm)
        <TimeWindow: 2013-12-03 00:00:00..2013-12-04 00:00:00>

    """


def doctest_TimeWindow_reread_no_file():
    """Test for TimeWindow.reread

        >>> window = make_time_window('/nosuchfile')

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

        >>> window = make_time_window(sampledata, min, max, vm)

    There's no error, the line with a bad timestamp is silently skipped.

        >>> len(window.items)
        2

    """


def doctest_TimeWindow_reread_bad_ordering():
    """Test for TimeWindow.reread

        >>> from datetime import datetime
        >>> min = datetime(2013, 12, 4)
        >>> max = datetime(2013, 12, 5)

        >>> sampledata = StringIO('''
        ... 2013-12-04 09:00: start **
        ... 2013-12-04 09:14: gtimelog: write some tests
        ... 2013-12-04 09:10: gtimelog: whoops clock got all confused
        ... 2013-12-04 09:10: gtimelog: so this will need to be fixed
        ... ''')

        >>> window = make_time_window(sampledata, min, max)

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

        >>> window = make_time_window(sampledata, min, max, vm)
        >>> window.count_days()
        3

    """


def doctest_TimeWindow_last_entry():
    """Test for TimeWindow.last_entry

        >>> from datetime import datetime
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


def doctest_Exports_to_csv_complete():
    r"""Tests for Exports.to_csv_complete

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

        >>> window = make_time_window(sampledata, min, max, vm)

        >>> Exports(window).to_csv_complete(sys.stdout)
        task,time (minutes)
        etc,60
        something,45
        something else,105

    """


def doctest_Exports_to_csv_daily():
    r"""Tests for Exports.to_csv_daily

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

        >>> window = make_time_window(sampledata, min, max, vm)

        >>> Exports(window).to_csv_daily(sys.stdout)
        date,day-start (hours),slacking (hours),work (hours)
        2008-06-03,12.75,0.0,3.0
        2008-06-04,0.0,0.0,0.0
        2008-06-05,12.75,1.0,0.5

    """


def doctest_Exports_icalendar():
    r"""Tests for Exports.icalendar

        >>> from datetime import datetime, time
        >>> min = datetime(2008, 6, 1)
        >>> max = datetime(2008, 7, 1)
        >>> vm = time(2, 0)

        >>> sampledata = StringIO(r'''
        ... 2008-06-03 12:45: start **
        ... 2008-06-03 13:00: something
        ... 2008-06-03 15:45: something, else; with special\chars
        ... 2008-06-05 12:45: start **
        ... 2008-06-05 13:15: something
        ... 2008-06-05 14:15: rest **
        ... ''')

        >>> window = make_time_window(sampledata, min, max, vm)

        >>> with freezegun.freeze_time("2015-05-18 15:40"):
        ...     with mock.patch('socket.getfqdn') as mock_getfqdn:
        ...         mock_getfqdn.return_value = 'localhost'
        ...         Exports(window).icalendar(sys.stdout)
        ... # doctest: +REPORT_NDIFF
        BEGIN:VCALENDAR
        PRODID:-//gtimelog.org/NONSGML GTimeLog//EN
        VERSION:2.0
        BEGIN:VEVENT
        UID:be5f9be205c2308f7f1a30d6c399d6bd@localhost
        SUMMARY:start **
        DTSTART:20080603T124500
        DTEND:20080603T124500
        DTSTAMP:20150518T154000Z
        END:VEVENT
        BEGIN:VEVENT
        UID:33c7e212fed11eda71d5acd4bd22119b@localhost
        SUMMARY:something
        DTSTART:20080603T124500
        DTEND:20080603T130000
        DTSTAMP:20150518T154000Z
        END:VEVENT
        BEGIN:VEVENT
        UID:b10c11beaf91df16964a46b4c87420b1@localhost
        SUMMARY:something\, else\; with special\\chars
        DTSTART:20080603T130000
        DTEND:20080603T154500
        DTSTAMP:20150518T154000Z
        END:VEVENT
        BEGIN:VEVENT
        UID:04964eef67ec22178d74fe4c0f06aa2a@localhost
        SUMMARY:start **
        DTSTART:20080605T124500
        DTEND:20080605T124500
        DTSTAMP:20150518T154000Z
        END:VEVENT
        BEGIN:VEVENT
        UID:2b51ea6d1c26f02d58051a691657068d@localhost
        SUMMARY:something
        DTSTART:20080605T124500
        DTEND:20080605T131500
        DTSTAMP:20150518T154000Z
        END:VEVENT
        BEGIN:VEVENT
        UID:bd6bfd401333dbbf34fec941567d5d06@localhost
        SUMMARY:rest **
        DTSTART:20080605T131500
        DTEND:20080605T141500
        DTSTAMP:20150518T154000Z
        END:VEVENT
        END:VCALENDAR

    """


def doctest_Reports_weekly_report_categorized():
    r"""Tests for Reports.weekly_report_categorized

        >>> from datetime import datetime

        >>> min = datetime(2010, 1, 25)
        >>> max = datetime(2010, 1, 31)

        >>> window = make_time_window(min=min, max=max)
        >>> reports = Reports(window)
        >>> reports.weekly_report_categorized(sys.stdout, 'foo@bar.com',
        ...                                   'Bob Jones')
        To: foo@bar.com
        Subject: Weekly report for Bob Jones (week 04)
        <BLANKLINE>
        No work done this week.

        >>> fh = StringIO(textwrap.dedent('''
        ...    2010-01-30 09:00: start **
        ...    2010-01-30 09:23: Bing: stuff
        ...    2010-01-30 12:54: Bong: other stuff
        ...    2010-01-30 13:32: lunch **
        ...    2010-01-30 23:46: misc: blah
        ... '''))

        >>> window = make_time_window(fh, min, max)
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
        misc:
        <BLANKLINE>
          Blah                                                           10:14
        ----------------------------------------------------------------------
                                                                         10:14
        <BLANKLINE>
        Total work done this week: 14:08
        <BLANKLINE>
        Categories by time spent:
          misc            10:14
          Bong             3:31
          Bing             0:23

    """


def doctest_Reports_monthly_report_categorized():
    r"""Tests for Reports.monthly_report_categorized

        >>> from datetime import datetime, time

        >>> vm = time(2, 0)
        >>> min = datetime(2010, 1, 25)
        >>> max = datetime(2010, 1, 31)

        >>> window = make_time_window(min=min, max=max)
        >>> reports = Reports(window)
        >>> reports.monthly_report_categorized(sys.stdout, 'foo@bar.com',
        ...                                   'Bob Jones')
        To: foo@bar.com
        Subject: Monthly report for Bob Jones (2010/01)
        <BLANKLINE>
        No work done this month.

        >>> fh = StringIO(textwrap.dedent('''
        ...    2010-01-28 09:00: start
        ...    2010-01-28 09:23: give up ***
        ...
        ...    2010-01-30 09:00: start
        ...    2010-01-30 09:23: Bing: stuff
        ...    2010-01-30 12:54: Bong: other stuff
        ...    2010-01-30 13:32: lunch **
        ...    2010-01-30 23:46: misc
        ... '''))

        >>> window = make_time_window(fh, min, max, vm)
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

        >>> from datetime import datetime, time, timedelta

        >>> vm = time(2, 0)
        >>> min = datetime(2010, 1, 25)
        >>> max = datetime(2010, 1, 31)

        >>> categories = {
        ...    'Bing': timedelta(2),
        ...    None: timedelta(1)}

        >>> window = make_time_window(StringIO(), min, max, vm)
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

        >>> from datetime import datetime, time

        >>> vm = time(2, 0)
        >>> min = datetime(2010, 1, 30)
        >>> max = datetime(2010, 1, 31)

        >>> window = make_time_window(StringIO(), min, max, vm)
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

        >>> window = make_time_window(fh, min, max, vm)
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

        >>> from datetime import datetime, time

        >>> vm = time(2, 0)
        >>> min = datetime(2010, 1, 25)
        >>> max = datetime(2010, 1, 31)

        >>> window = make_time_window(StringIO(), min, max, vm)
        >>> reports = Reports(window)
        >>> reports.weekly_report_plain(sys.stdout, 'foo@bar.com', 'Bob Jones')
        To: foo@bar.com
        Subject: Weekly report for Bob Jones (week 04)
        <BLANKLINE>
        No work done this week.

        >>> fh = StringIO(textwrap.dedent('''
        ...    2010-01-28 09:00: start
        ...    2010-01-28 09:23: give up ***
        ...
        ...    2010-01-30 09:00: start
        ...    2010-01-30 09:23: Bing: stuff
        ...    2010-01-30 12:54: Bong: other stuff
        ...    2010-01-30 13:32: lunch **
        ...    2010-01-30 15:46: misc
        ... '''))

        >>> window = make_time_window(fh, min, max, vm)
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

        >>> from datetime import datetime, time

        >>> vm = time(2, 0)
        >>> min = datetime(2007, 9, 1)
        >>> max = datetime(2007, 10, 1)

        >>> window = make_time_window(StringIO(), min, max, vm)
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

        >>> window = make_time_window(fh, min, max, vm)
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

        >>> from datetime import datetime, time

        >>> vm = time(2, 0)
        >>> min = datetime(2010, 1, 25)
        >>> max = datetime(2010, 2, 1)

        >>> window = make_time_window(StringIO(), min, max, vm)
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

        >>> window = make_time_window(fh, min, max, vm)
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


class Mixins(object):

    tempdir = None

    def mkdtemp(self):
        if self.tempdir is None:
            self.tempdir = tempfile.mkdtemp(prefix='gtimelog-test-')
            self.addCleanup(shutil.rmtree, self.tempdir)
        return self.tempdir

    def tempfile(self, filename='timelog.txt'):
        return os.path.join(self.mkdtemp(), filename)

    def write_file(self, filename, content):
        filename = os.path.join(self.mkdtemp(), filename)
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        return filename


class TestTimeCollection(Mixins, unittest.TestCase):

    def test_split_category(self):
        sp = TimeCollection.split_category
        self.assertEqual(sp('some task'), (None, 'some task'))
        self.assertEqual(sp('project: some task'), ('project', 'some task'))
        self.assertEqual(sp('project: some task: etc'),
                         ('project', 'some task: etc'))

    def test_split_category_no_task_just_category(self):
        # Regression test for https://github.com/gtimelog/gtimelog/issues/117
        sp = TimeCollection.split_category
        self.assertEqual(sp('project: '), ('project', ''))
        self.assertEqual(sp('project:'), ('project', ''))

    def test_sorted_grouped_time_collection(self):
        # the unsorted list is nromally a TimeCollection but we fake it
        unsorted_list = (  # list of (start-time, name, duration)
            (10_000, 'BBB: b', 20),
            (30_000, 'CCC: c', 10),
            (20_000, 'Alone', 12),
            (40_000, 'AAA: a', 15),
        )
        taskfile = self.write_file('tasks.txt', textwrap.dedent('''\
            Alone
            # comments are skipped
            BBB: b
            AAA: a
            CCC: c
        '''))
        tasklist = TaskList(taskfile)
        sorted_by = {
            'start-time': ('BBB: b', 'Alone', 'CCC: c', 'AAA: a'),
            'name': ('AAA: a', 'Alone', 'BBB: b', 'CCC: c'),
            'duration': ('CCC: c', 'Alone', 'AAA: a', 'BBB: b'),
            'task-list': ('Alone', 'BBB: b', 'AAA: a', 'CCC: c'),
        }

        def tc_sorted(method):
            tc_key = TimeCollection._get_grouped_order_key
            return tuple(name for start_time, name, duration in
                         sorted(unsorted_list, key=tc_key(method, tasklist)))

        # we could have a loop but then it wouldn't be clear with which
        # method the assert fails
        self.assertEqual(tc_sorted('start-time'), sorted_by['start-time'])
        self.assertEqual(tc_sorted('name'), sorted_by['name'])
        self.assertEqual(tc_sorted('duration'), sorted_by['duration'])
        self.assertEqual(tc_sorted('task-list'), sorted_by['task-list'])


class TestTaskList(Mixins, unittest.TestCase):

    def test_missing_file(self):
        tasklist = TaskList('/nosuchfile')
        self.assertFalse(tasklist.check_reload())
        tasklist.reload()  # no crash

    def test_parsing_and_ordering(self):
        taskfile = self.write_file('tasks.txt', textwrap.dedent('''\
            # comments are skipped
            some task
            other task
            project: do it
            project:fix bugs
            misc: paperwork
        '''))
        tasklist = TaskList(taskfile)
        self.assertEqual(tasklist.groups, [
            ('project', ['do it', 'fix bugs']),
            ('misc', ['paperwork']),
            ('Other', ['some task', 'other task']),
        ])
        # also test that the order function works as foreseen
        self.assertEqual(tasklist.order('project: fix bugs'), 4)
        self.assertEqual(tasklist.order('unknown task'),  sys.maxsize)

    def test_unicode(self):
        taskfile = self.write_file('tasks.txt', '\N{SNOWMAN}')
        tasklist = TaskList(taskfile)
        self.assertEqual(tasklist.groups, [
            ('Other', ['\N{SNOWMAN}']),
        ])

    def test_reloading(self):
        taskfile = self.write_file('tasks.txt', 'some tasks\n')
        couple_seconds_ago = time.time() - 2
        os.utime(taskfile, (couple_seconds_ago, couple_seconds_ago))

        tasklist = TaskList(taskfile)
        self.assertEqual(tasklist.groups, [
            ('Other', ['some tasks']),
        ])
        self.assertFalse(tasklist.check_reload())

        with open(taskfile, 'w') as f:
            f.write('new tasks\n')

        self.assertTrue(tasklist.check_reload())

        self.assertEqual(tasklist.groups, [
            ('Other', ['new tasks']),
        ])


class TestTimeLog(Mixins, unittest.TestCase):

    def test_reloading(self):
        logfile = self.tempfile()
        timelog = TimeLog(logfile, datetime.time(2, 0))
        # No file - nothing to reload
        self.assertFalse(timelog.check_reload())
        # Create a file - it should be reloaded, once.
        open(logfile, 'w').close()
        self.assertTrue(timelog.check_reload())
        self.assertFalse(timelog.check_reload())
        # Change the timestamp, somehow
        st = os.stat(logfile)
        os.utime(logfile, (st.st_atime, st.st_mtime + 1))
        self.assertTrue(timelog.check_reload())
        self.assertFalse(timelog.check_reload())
        # Disappearance of the file is noticed
        os.unlink(logfile)
        self.assertTrue(timelog.check_reload())
        self.assertFalse(timelog.check_reload())

    def test_window_for_day(self):
        timelog = TimeLog(StringIO(), datetime.time(2, 0))
        window = timelog.window_for_day(datetime.date(2015, 9, 17))
        self.assertEqual(window.min_timestamp, datetime.datetime(2015, 9, 17, 2, 0))
        self.assertEqual(window.max_timestamp, datetime.datetime(2015, 9, 18, 2, 0))

    def test_window_for_week(self):
        timelog = TimeLog(StringIO(), datetime.time(2, 0))
        for d in range(14, 21):
            window = timelog.window_for_week(datetime.date(2015, 9, d))
            self.assertEqual(window.min_timestamp, datetime.datetime(2015, 9, 14, 2, 0))
            self.assertEqual(window.max_timestamp, datetime.datetime(2015, 9, 21, 2, 0))

    def test_window_for_month(self):
        timelog = TimeLog(StringIO(), datetime.time(2, 0))
        for d in range(1, 31):
            window = timelog.window_for_month(datetime.date(2015, 9, d))
            self.assertEqual(window.min_timestamp, datetime.datetime(2015, 9, 1, 2, 0))
            self.assertEqual(window.max_timestamp, datetime.datetime(2015, 10, 1, 2, 0))

    def test_window_for_date_range(self):
        timelog = TimeLog(StringIO(), datetime.time(2, 0))
        window = timelog.window_for_date_range(datetime.date(2015, 9, 3),
                                               datetime.date(2015, 9, 24))
        self.assertEqual(window.min_timestamp, datetime.datetime(2015, 9, 3, 2, 0))
        self.assertEqual(window.max_timestamp, datetime.datetime(2015, 9, 25, 2, 0))

    def test_appending_clears_window_cache(self):
        # Regression test for https://github.com/gtimelog/gtimelog/issues/28
        timelog = TimeLog(self.tempfile(), datetime.time(2, 0))

        w = timelog.window_for_day(datetime.date(2014, 11, 12))
        self.assertEqual(list(w.all_entries()), [])

        timelog.append('started **', now=datetime.datetime(2014, 11, 12, 10, 00))
        w = timelog.window_for_day(datetime.date(2014, 11, 12))
        self.assertEqual(len(list(w.all_entries())), 1)

    def test_append_adds_blank_line_on_new_day(self):
        timelog = TimeLog(self.tempfile(), datetime.time(2, 0))
        timelog.append('working on sth', now=datetime.datetime(2014, 11, 12, 18, 0))
        timelog.append('new day **', now=datetime.datetime(2014, 11, 13, 8, 0))
        with open(timelog.filename, 'r') as f:
            self.assertEqual(f.readlines(),
                             ['2014-11-12 18:00: working on sth\n',
                              '\n',
                              '2014-11-13 08:00: new day **\n'])

    @freezegun.freeze_time("2015-05-12 16:27:35.115265")
    def test_append_rounds_the_time(self):
        timelog = TimeLog(self.tempfile(), datetime.time(2, 0))
        timelog.append('now')
        self.assertEqual(timelog.items[-1][0], datetime.datetime(2015, 5, 12, 16, 27))

    @freezegun.freeze_time("2018-12-09 16:27")
    def test_remove_last_entry(self):
        TEST_TIMELOG = textwrap.dedent("""
            2018-12-09 08:30: start at home
            2018-12-09 08:40: emails
            # comment
            2018-12-09 12:15: coding
        """)
        filename = self.tempfile()
        self.write_file(filename, TEST_TIMELOG)
        timelog = TimeLog(filename, datetime.time(2, 0))
        last_entry = timelog.remove_last_entry()
        self.assertEqual(last_entry, 'coding')
        items_after_call = [
            (datetime.datetime(2018, 12, 9, 8, 30), 'start at home'),
            (datetime.datetime(2018, 12, 9, 8, 40), 'emails')]
        self.assertEqual(timelog.items, items_after_call)
        self.assertEqual(timelog.window.items, items_after_call)
        with open(filename) as f:
            self.assertEqual(f.read(), textwrap.dedent("""
                2018-12-09 08:30: start at home
                2018-12-09 08:40: emails
                # comment
                ##2018-12-09 12:15: coding
            """))

        last_entry = timelog.remove_last_entry()
        self.assertEqual(last_entry, 'emails')
        items_after_call = [
            (datetime.datetime(2018, 12, 9, 8, 30), 'start at home')]
        self.assertEqual(timelog.items, items_after_call)
        self.assertEqual(timelog.window.items, items_after_call)
        with open(filename) as f:
            self.assertEqual(f.read(), textwrap.dedent("""
                2018-12-09 08:30: start at home
                ##2018-12-09 08:40: emails
                # comment
                ##2018-12-09 12:15: coding
            """))

    @freezegun.freeze_time("2018-12-10 10:40")
    def test_remove_last_entry_start_of_day(self):

        TEST_TIMELOG = textwrap.dedent("""
            2018-12-09 08:30: start at home
            2018-12-09 08:40: emails

            2018-12-10 08:30: start at home
        """)

        filename = self.tempfile()
        self.write_file(filename, TEST_TIMELOG)
        timelog = TimeLog(filename, datetime.time(2, 0))
        timelog.reread()
        last_entry = timelog.remove_last_entry()
        self.assertEqual(last_entry, 'start at home')
        items_after_call = [
            (datetime.datetime(2018, 12, 9, 8, 30), 'start at home'),
            (datetime.datetime(2018, 12, 9, 8, 40), 'emails')]
        self.assertEqual(timelog.items, items_after_call)
        self.assertEqual(timelog.window.items, [])
        with open(filename) as f:
            self.assertEqual(f.read(), textwrap.dedent("""
                2018-12-09 08:30: start at home
                2018-12-09 08:40: emails

                ##2018-12-10 08:30: start at home
            """))

        # no further remove possible at beginning of the day:
        last_entry = timelog.remove_last_entry()
        self.assertIsNone(last_entry)

    @freezegun.freeze_time("2015-05-12 16:27")
    def test_valid_time_accepts_any_time_in_the_past_when_log_is_empty(self):
        timelog = TimeLog(StringIO(), datetime.time(2, 0))
        past = datetime.datetime(2015, 5, 12, 14, 20)
        self.assertTrue(timelog.valid_time(past))

    @freezegun.freeze_time("2015-05-12 16:27")
    def test_valid_time_rejects_times_in_the_future(self):
        timelog = TimeLog(StringIO(), datetime.time(2, 0))
        future = datetime.datetime(2015, 5, 12, 16, 30)
        self.assertFalse(timelog.valid_time(future))

    @freezegun.freeze_time("2015-05-12 16:27")
    def test_valid_time_rejects_times_before_last_entry(self):
        timelog = TimeLog(StringIO("2015-05-12 15:00: did stuff"),
                          datetime.time(2, 0))
        past = datetime.datetime(2015, 5, 12, 14, 20)
        self.assertFalse(timelog.valid_time(past))

    @freezegun.freeze_time("2015-05-12 16:27")
    def test_valid_time_accepts_times_between_last_entry_and_now(self):
        timelog = TimeLog(StringIO("2015-05-12 15:00: did stuff"),
                          datetime.time(2, 0))
        past = datetime.datetime(2015, 5, 12, 15, 20)
        self.assertTrue(timelog.valid_time(past))

    def test_parse_correction_leaves_regular_text_alone(self):
        timelog = TimeLog(StringIO(), datetime.time(2, 0))
        self.assertEqual(timelog.parse_correction("did stuff"),
                         ("did stuff", None))

    @freezegun.freeze_time("2015-05-12 16:27")
    def test_parse_correction_recognizes_absolute_times(self):
        timelog = TimeLog(StringIO(), datetime.time(2, 0))
        self.assertEqual(timelog.parse_correction("15:20 did stuff"),
                         ("did stuff", datetime.datetime(2015, 5, 12, 15, 20)))

    @freezegun.freeze_time("2015-05-13 00:27")
    def test_parse_correction_handles_virtual_midnight_yesterdays_time(self):
        # Regression test for https://github.com/gtimelog/gtimelog/issues/33
        timelog = TimeLog(StringIO(), datetime.time(2, 0))
        self.assertEqual(timelog.parse_correction("15:20 did stuff"),
                         ("did stuff", datetime.datetime(2015, 5, 12, 15, 20)))

    @freezegun.freeze_time("2015-05-13 00:27")
    def test_parse_correction_handles_virtual_midnight_todays_time(self):
        timelog = TimeLog(StringIO(), datetime.time(2, 0))
        self.assertEqual(timelog.parse_correction("00:15 did stuff"),
                         ("did stuff", datetime.datetime(2015, 5, 13, 00, 15)))

    @freezegun.freeze_time("2015-05-12 16:27")
    def test_parse_correction_ignores_future_absolute_times(self):
        timelog = TimeLog(StringIO(), datetime.time(2, 0))
        self.assertEqual(timelog.parse_correction("17:20 did stuff"),
                         ("17:20 did stuff", None))

    @freezegun.freeze_time("2015-05-12 16:27")
    def test_parse_correction_ignores_bad_absolute_times(self):
        timelog = TimeLog(StringIO(), datetime.time(2, 0))
        self.assertEqual(timelog.parse_correction("19:60 did stuff"),
                         ("19:60 did stuff", None))
        self.assertEqual(timelog.parse_correction("24:00 did stuff"),
                         ("24:00 did stuff", None))

    @freezegun.freeze_time("2015-05-12 16:27")
    def test_parse_correction_ignores_absolute_times_before_last_entry(self):
        timelog = TimeLog(StringIO("2015-05-12 16:00: stuff"),
                          datetime.time(2, 0))
        self.assertEqual(timelog.parse_correction("15:20 did stuff"),
                         ("15:20 did stuff", None))

    @freezegun.freeze_time("2015-05-12 16:27")
    def test_parse_correction_recognizes_negative_relative_times(self):
        timelog = TimeLog(StringIO(), datetime.time(2, 0))
        self.assertEqual(timelog.parse_correction("-20 did stuff"),
                         ("did stuff", datetime.datetime(2015, 5, 12, 16, 7)))

    @freezegun.freeze_time("2015-05-12 16:27")
    def test_parse_correction_recognizes_positive_relative_times(self):
        timelog = TimeLog(StringIO("2015-05-12 15:50: stuff"),
                          datetime.time(2, 0))
        self.assertEqual(timelog.parse_correction("+20 did stuff"),
                         ("did stuff", datetime.datetime(2015, 5, 12, 16, 10)))

    @freezegun.freeze_time("2015-05-12 16:27")
    def test_parse_correction_ignores_positive_relative_times_without_initial_entry(self):
        timelog = TimeLog(StringIO(), datetime.time(2, 0))
        self.assertEqual(timelog.parse_correction("+20 did stuff"),
                         ("+20 did stuff", None))

    @freezegun.freeze_time("2015-05-12 16:27")
    def test_parse_correction_ignores_negative_relative_times_before_last_entry(self):
        timelog = TimeLog(StringIO("2015-05-12 16:00: stuff"),
                          datetime.time(2, 0))
        self.assertEqual(timelog.parse_correction("-30 did stuff"),
                         ("-30 did stuff", None))

    @freezegun.freeze_time("2015-05-12 16:27")
    def test_parse_correction_ignores_positive_relative_times_in_the_future(self):
        timelog = TimeLog(StringIO("2015-05-12 15:50: stuff"),
                          datetime.time(2, 0))
        self.assertEqual(timelog.parse_correction("+40 did stuff"),
                         ("+40 did stuff", None))

    @freezegun.freeze_time("2015-05-12 16:27")
    def test_parse_correction_ignores_bad_negative_relative_times(self):
        timelog = TimeLog(StringIO(), datetime.time(2, 0))
        self.assertEqual(timelog.parse_correction("-200 did stuff"),
                         ("-200 did stuff", None))

    @freezegun.freeze_time("2015-05-12 16:27")
    def test_parse_correction_ignores_bad_positive_relative_times(self):
        timelog = TimeLog(StringIO("2015-05-12 15:50: stuff"),
                          datetime.time(2, 0))
        self.assertEqual(timelog.parse_correction("+200 did stuff"),
                         ("+200 did stuff", None))


class TestTotals(unittest.TestCase):

    TEST_TIMELOG = textwrap.dedent(
        """
        2018-12-09 08:30: start at home
        2018-12-09 08:40: emails
        2018-12-09 09:10: travel to work ***
        2018-12-09 09:15: coffee **
        2018-12-09 12:15: coding
        """)

    def setUp(self):
        self.tw = make_time_window(
            StringIO(self.TEST_TIMELOG),
            datetime.datetime(2018, 12, 9, 8, 0),
            datetime.datetime(2018, 12, 9, 23, 59),
            datetime.time(2, 0),
        )

    def test_TimeWindow_totals(self):
        work, slack = self.tw.totals()
        self.assertEqual(work, datetime.timedelta(hours=3, minutes=10))
        self.assertEqual(slack, datetime.timedelta(hours=0, minutes=5))


class TestFiltering(unittest.TestCase):

    TEST_TIMELOG = textwrap.dedent("""
        2014-05-27 10:03: arrived
        2014-05-27 10:13: edx: introduce topic to new sysadmins
        2014-05-27 10:30: email
        2014-05-27 12:11: meeting: how to support new courses?
        2014-05-27 15:12: edx: write test procedure for EdX instances
        2014-05-27 17:03: cluster: set-up accounts, etc.
        2014-05-27 17:14: support: how to run statistics on Hydra?
        2014-05-27 17:36: off: pause **
        2014-05-27 17:38: email
        2014-05-27 19:06: off: dinner & family **
        2014-05-27 22:19: cluster: fix shmmax-shmall issue
        """)

    def setUp(self):
        self.tw = make_time_window(
            StringIO(self.TEST_TIMELOG),
            datetime.datetime(2014, 5, 27, 9, 0),
            datetime.datetime(2014, 5, 27, 23, 59),
            datetime.time(2, 0),
        )

    def test_TimeWindow_totals_filtering1(self):
        work, slack = self.tw.totals(filter_text='support')
        # matches two items: 1h 41m (10:30--12:11) + 11m (17:03--17:14)
        self.assertEqual(work, datetime.timedelta(hours=1, minutes=52))
        self.assertEqual(slack, datetime.timedelta(0))

    def test_TimeWindow_totals_filtering2(self):
        work, slack = self.tw.totals(filter_text='f')
        # matches four items:
        # 3h  1m (12:11--15:12) edx: write test procedure [f]or EdX instances
        # 3h 13m (19:06--22:19) cluster: [f]ix shmmax-shmall issue
        # total work: 6h 14m
        #    22m (17:14--17:36) o[f]f: pause **
        # 1h 28m (17:38--19:06) o[f]f: dinner & family **
        # total slacking: 1h 50m
        self.assertEqual(work, datetime.timedelta(hours=6, minutes=14))
        self.assertEqual(slack, datetime.timedelta(hours=1, minutes=50))


class TestTagging(unittest.TestCase):

    TEST_TIMELOG = textwrap.dedent("""
        2014-05-27 10:03: arrived
        2014-05-27 10:13: edx: introduce topic to new sysadmins -- edx
        2014-05-27 10:30: email
        2014-05-27 12:11: meeting: how to support new courses?  -- edx meeting
        2014-05-27 15:12: edx: write test procedure for EdX instances -- edx sysadmin
        2014-05-27 17:03: cluster: set-up accounts, etc. -- sysadmin hpc
        2014-05-27 17:14: support: how to run statistics on Hydra? -- support hydra
        2014-05-27 17:36: off: pause **
        2014-05-27 17:38: email
        2014-05-27 19:06: off: dinner & family **
        2014-05-27 22:19: cluster: fix shmmax-shmall issue -- sysadmin hpc
        """)

    def setUp(self):
        self.tw = make_time_window(
            StringIO(self.TEST_TIMELOG),
            datetime.datetime(2014, 5, 27, 9, 0),
            datetime.datetime(2014, 5, 27, 23, 59),
            datetime.time(2, 0),
        )

    def test_TimeWindow_set_of_all_tags(self):
        tags = self.tw.set_of_all_tags()
        self.assertEqual(tags, {'edx', 'hpc', 'hydra', 'meeting',
                                'support', 'sysadmin'})

    def test_TimeWindow_totals_per_tag1(self):
        """Test aggregate time per tag, 1 entry only"""
        result = self.tw.totals('meeting')
        self.assertEqual(len(result), 2)
        work, slack = result
        self.assertEqual(work,
            # start/end times are manually extracted from the TEST_TIMELOG sample
            (datetime.timedelta(hours=12, minutes=11) - datetime.timedelta(hours=10, minutes=30))
        )
        self.assertEqual(slack, datetime.timedelta(0))

    def test_TimeWindow_totals_per_tag2(self):
        """Test aggregate time per tag, several entries"""
        result = self.tw.totals('hpc')
        self.assertEqual(len(result), 2)
        work, slack = result
        self.assertEqual(work,
            # start/end times are manually extracted from the TEST_TIMELOG sample
            (datetime.timedelta(hours=17, minutes=3) - datetime.timedelta(hours=15, minutes=12))
            + (datetime.timedelta(hours=22, minutes=19) - datetime.timedelta(hours=19, minutes=6))
        )
        self.assertEqual(slack, datetime.timedelta(0))

    def test_TimeWindow__split_entry_and_tags1(self):
        """Test `TimeWindow._split_entry_and_tags` with simple entry"""
        result = self.tw._split_entry_and_tags('email')
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], 'email')
        self.assertEqual(result[1], set())

    def test_TimeWindow__split_entry_and_tags2(self):
        """Test `TimeWindow._split_entry_and_tags` with simple entry and tags"""
        result = self.tw._split_entry_and_tags('restart CFEngine server -- sysadmin cfengine issue327')
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], 'restart CFEngine server')
        self.assertEqual(result[1], {'sysadmin', 'cfengine', 'issue327'})

    def test_TimeWindow__split_entry_and_tags3(self):
        """Test `TimeWindow._split_entry_and_tags` with category, entry, and tags"""
        result = self.tw._split_entry_and_tags('tooling: tagging support in gtimelog -- tooling gtimelog')
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], 'tooling: tagging support in gtimelog')
        self.assertEqual(result[1], {'tooling', 'gtimelog'})

    def test_TimeWindow__split_entry_and_tags4(self):
        """Test `TimeWindow._split_entry_and_tags` with slack-type entry"""
        result = self.tw._split_entry_and_tags('read news -- reading **')
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], 'read news **')
        self.assertEqual(result[1], {'reading'})

    def test_TimeWindow__split_entry_and_tags5(self):
        """Test `TimeWindow._split_entry_and_tags` with slack-type entry"""
        result = self.tw._split_entry_and_tags('read news -- reading ***')
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], 'read news ***')
        self.assertEqual(result[1], {'reading'})

    def test_Reports__report_tags(self):
        rp = Reports(self.tw)
        txt = StringIO()
        # use same tags as in tests above, so we know the totals
        rp._report_tags(txt, ['meeting', 'hpc'])
        self.assertEqual(
            txt.getvalue().strip(),
            textwrap.dedent("""
            Time spent in each area:

              hpc          5:04
              meeting      1:41

            Note that area totals may not add up to the period totals,
            as each entry may be belong to multiple areas (or none at all).
            """).strip())

    def test_Reports_daily_report_includes_tags(self):
        rp = Reports(self.tw)
        txt = StringIO()
        rp.daily_report(txt, 'me@example.com', 'me')
        self.assertIn('Time spent in each area', txt.getvalue())

    def test_Reports_weekly_report_includes_tags(self):
        rp = Reports(self.tw)
        txt = StringIO()
        rp.weekly_report(txt, 'me@example.com', 'me')
        self.assertIn('Time spent in each area', txt.getvalue())

    def test_Reports_monthly_report_includes_tags(self):
        rp = Reports(self.tw)
        txt = StringIO()
        rp.monthly_report(txt, 'me@example.com', 'me')
        self.assertIn('Time spent in each area', txt.getvalue())

    def test_Reports_categorized_report_includes_tags(self):
        rp = Reports(self.tw, style='categorized')
        txt = StringIO()
        rp.weekly_report(txt, 'me@example.com', 'me')
        self.assertIn('Time spent in each area', txt.getvalue())
        txt = StringIO()
        rp.monthly_report(txt, 'me@example.com', 'me')
        self.assertIn('Time spent in each area', txt.getvalue())


class TestReportRecord(Mixins, unittest.TestCase):

    def setUp(self):
        self.filename = self.tempfile('sentreports.log')

    def load_fixture(self, lines):
        with open(self.filename, 'w') as f:
            for line in lines:
                f.write(line + '\n')

    def test_get_report_id(self):
        get_id = ReportRecord.get_report_id
        self.assertEqual(
            get_id(ReportRecord.WEEKLY, datetime.date(2016, 1, 1)),
            '2015/53',
        )

    @freezegun.freeze_time("2016-01-08 09:34:50")
    def test_record(self):
        rr = ReportRecord(self.filename)
        rr.record(rr.DAILY, datetime.date(2016, 1, 6), 'test@example.com')
        rr.record(rr.WEEKLY, datetime.date(2016, 1, 6), 'test@example.com')
        rr.record(rr.MONTHLY, datetime.date(2016, 1, 6), 'test@example.com')
        with open(self.filename) as f:
            written = f.read()
        self.assertEqual(
            written.splitlines(),
            [
                "2016-01-08 09:34:50,daily,2016-01-06,test@example.com",
                "2016-01-08 09:34:50,weekly,2016/1,test@example.com",
                "2016-01-08 09:34:50,monthly,2016-01,test@example.com",
            ]
        )

    def test_get_recipients(self):
        self.load_fixture([
            "2015-12-21 12:15:11,daily,2015-12-21,test@example.com",
            "2015-12-21 12:17:35,daily,2015-12-21,marius+test@example.com",
            "2015-12-21 12:18:21,daily,2015-12-21,marius+test@example.com",
            "2015-12-21 12:19:06,weekly,2015/46,marius+test@example.com",
            "2016-01-04 10:35:09,weekly,2015/53,activity@example.com",
            "2016-01-04 11:00:33,monthly,2015-12,activity@example.com",
            "2016-01-04 12:59:24,weekly,2015/49,activity@example.com",
            "2016-01-04 12:59:37,weekly,2015/52,activity@example.com",
        ])
        rr = ReportRecord(self.filename)
        self.assertEqual(
            rr.get_recipients(rr.DAILY, datetime.date(2016, 1, 6)),
            [],
        )
        self.assertEqual(
            rr.get_recipients(rr.DAILY, datetime.date(2015, 12, 21)),
            [
                "test@example.com",
                "marius+test@example.com",
                "marius+test@example.com",
            ],
        )
        self.assertEqual(
            rr.get_recipients(rr.WEEKLY, datetime.date(2015, 12, 21)),
            [
                "activity@example.com",
            ],
        )

    def test_reread_missing_file(self):
        rr = ReportRecord(self.filename)
        rr.reread()
        self.assertEqual(len(rr._records), 0)

    def test_reread_bad_records_are_ignored(self):
        self.load_fixture([
            "2016-01-08 09:34:50,daily,2016-01-06,test@example.com",
            "Somebody might edit this file and corrupt it",
            "2016-01-08 09:34:50,monthly,2016-01,test@example.com",
        ])
        rr = ReportRecord(self.filename)
        rr.reread()
        self.assertEqual(len(rr._records), 2)

    def test_record_then_load_when_empty(self):
        rr = ReportRecord(self.filename)
        now = datetime.datetime(2016, 1, 8, 9, 34, 50)
        rr.record(rr.DAILY, datetime.date(2016, 1, 6), 'test@example.com', now)
        self.assertEqual(
            rr.get_recipients(rr.DAILY, datetime.date(2016, 1, 6)),
            ['test@example.com']
        )

    def test_record_then_load_twice_when_empty(self):
        # Recording twice might not change the mtime because the resolution
        # is too low; so record() must update the internal data structures
        # by itself.
        rr = ReportRecord(self.filename)
        now = datetime.datetime(2016, 1, 8, 9, 34, 50)
        rr.record(rr.DAILY, datetime.date(2016, 1, 6), 'test@example.com', now)
        self.assertEqual(
            rr.get_recipients(rr.DAILY, datetime.date(2016, 1, 6)),
            ['test@example.com']
        )
        rr.record(rr.DAILY, datetime.date(2016, 1, 6), 'test@example.org', now)
        self.assertEqual(
            rr.get_recipients(rr.DAILY, datetime.date(2016, 1, 6)),
            ['test@example.com', 'test@example.org']
        )

    def test_record_then_load_when_nonempty(self):
        # Since we have lazy-loading, the "let's add the new record internally
        # and set last_mtime" optimization in record() might trick ReportRecord
        # into not loading an existing file at all.
        self.load_fixture([
            "2016-01-08 09:34:50,daily,2016-01-06,test@example.com",
            "2016-01-08 09:34:50,weekly,2016/1,test@example.com",
            "2016-01-08 09:34:50,monthly,2016-01,test@example.com",
        ])
        rr = ReportRecord(self.filename)
        now = datetime.datetime(2016, 1, 8, 9, 34, 50)
        rr.record(rr.DAILY, datetime.date(2016, 1, 6), 'test@example.org', now)
        self.assertEqual(
            rr.get_recipients(rr.DAILY, datetime.date(2016, 1, 6)),
            ['test@example.com', 'test@example.org']
        )

    def test_record_then_load_twice_when_nonempty(self):
        # I'm not sure what I'm protecting against with this test.  Probably
        # pure unnecessary paranoia.
        self.load_fixture([
            "2016-01-08 09:34:50,daily,2016-01-06,test@example.com",
            "2016-01-08 09:34:50,weekly,2016/1,test@example.com",
            "2016-01-08 09:34:50,monthly,2016-01,test@example.com",
        ])
        rr = ReportRecord(self.filename)
        now = datetime.datetime(2016, 1, 8, 9, 34, 50)
        rr.record(rr.DAILY, datetime.date(2016, 1, 6), 'test@example.org', now)
        rr.record(rr.DAILY, datetime.date(2016, 1, 6), 'test@example.net', now)
        self.assertEqual(
            rr.get_recipients(rr.DAILY, datetime.date(2016, 1, 6)),
            ['test@example.com', 'test@example.org', 'test@example.net']
        )

    def test_automatic_reload(self):
        rr = ReportRecord(self.filename)
        self.assertEqual(
            rr.get_recipients(rr.DAILY, datetime.date(2016, 1, 6)),
            []
        )
        self.load_fixture([
            "2016-01-08 09:34:50,daily,2016-01-06,test@example.com",
            "2016-01-08 09:34:50,weekly,2016/1,test@example.com",
            "2016-01-08 09:34:50,monthly,2016-01,test@example.com",
        ])
        self.assertEqual(
            rr.get_recipients(rr.DAILY, datetime.date(2016, 1, 6)),
            ['test@example.com']
        )


def additional_tests(): # for setup.py
    return doctest.DocTestSuite(optionflags=doctest.NORMALIZE_WHITESPACE,
                                checker=Checker())


def test_suite():
    return unittest.TestSuite([
        unittest.defaultTestLoader.loadTestsFromName(__name__),
        additional_tests(),
    ])
