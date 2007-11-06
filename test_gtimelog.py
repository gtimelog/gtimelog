#!/usr/bin/python
"""
Tests for gtimelog.py
"""

def doctest_format_duration():
    """Tests for format_duration.

        >>> from gtimelog import format_duration
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

        >>> from gtimelog import format_duration_short
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

        >>> from gtimelog import format_duration_long
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

        >>> from gtimelog import parse_datetime
        >>> parse_datetime('2005-02-03 02:13')
        datetime.datetime(2005, 2, 3, 2, 13)
        >>> parse_datetime('xyzzy')
        Traceback (most recent call last):
          ...
        ValueError: ('bad date time: ', 'xyzzy')

    """

def doctest_parse_time():
    """Tests for parse_time

        >>> from gtimelog import parse_time
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
        >>> from gtimelog import virtual_day

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
        >>> from gtimelog import different_days

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

def doctest_uniq():
    """Tests for uniq

        >>> from gtimelog import uniq
        >>> uniq(['a', 'b', 'b', 'c', 'd', 'b', 'd'])
        ['a', 'b', 'c', 'd', 'b', 'd']
        >>> uniq(['a'])
        ['a']
        >>> uniq([])
        []

    """

def doctest_TimeWindow_monthly_report():
    r"""Tests for TimeWindow.monthly_report

        >>> import sys

        >>> from datetime import datetime, time
        >>> from tempfile import NamedTemporaryFile
        >>> from gtimelog import TimeWindow

        >>> vm = time(2, 0)
        >>> min = datetime(2007, 9, 1)
        >>> max = datetime(2007, 10, 1)
        >>> fh = NamedTemporaryFile()

        >>> window = TimeWindow(fh.name, min, max, vm)
        >>> window.monthly_report(sys.stdout, 'foo@bar.com', 'Bob Jones')
        To: foo@bar.com
        Subject: Monthly report for Bob Jones (2007/09)
        <BLANKLINE>
        No work done this month.

        >>> _ = [fh.write(s + '\n') for s in [
        ...    '2007-09-30 09:00: start',
        ...    '2007-09-30 09:23: Bing: stuff',
        ...    '2007-09-30 12:54: Bong: other stuff',
        ...    '2007-09-30 13:32: lunch **',
        ...    '2007-09-30 15:46: misc',
        ...    '']]
        >>> fh.flush()

        >>> window = TimeWindow(fh.name, min, max, vm)
        >>> window.monthly_report(sys.stdout, 'foo@bar.com', 'Bob Jones')
        To: foo@bar.com
        Subject: Monthly report for Bob Jones (2007/09)
        <BLANKLINE>
        <BLANKLINE>
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

if __name__ == '__main__':
    import doctest
    fail, total = doctest.testmod()
    if not fail:
        print "%d tests passed." % total
