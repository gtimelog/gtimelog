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

def doctest_virtual_day():
    """Tests for virtual_day

        >>> from datetime import datetime
        >>> from gtimelog import virtual_day

    If this assumption fails, you will have to fix the test 

        >>> from gtimelog import virtual_midnight
        >>> virtual_midnight
        datetime.time(2, 0)

    The tests themselves:

        >>> virtual_day(datetime(2005, 2, 3, 1, 15))
        datetime.date(2005, 2, 2)
        >>> virtual_day(datetime(2005, 2, 3, 1, 59))
        datetime.date(2005, 2, 2)
        >>> virtual_day(datetime(2005, 2, 3, 2, 0))
        datetime.date(2005, 2, 3)
        >>> virtual_day(datetime(2005, 2, 3, 12, 0))
        datetime.date(2005, 2, 3)
        >>> virtual_day(datetime(2005, 2, 3, 23, 59))
        datetime.date(2005, 2, 3)

    """

def doctest_different_days():
    """Tests for different_days

        >>> from datetime import datetime
        >>> from gtimelog import different_days

    If this assumption fails, you will have to fix the test 

        >>> from gtimelog import virtual_midnight
        >>> virtual_midnight
        datetime.time(2, 0)

    The tests themselves:

        >>> different_days(datetime(2005, 2, 3, 1, 15),
        ...                datetime(2005, 2, 3, 2, 15))
        True
        >>> different_days(datetime(2005, 2, 3, 11, 15),
        ...                datetime(2005, 2, 3, 12, 15))
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

if __name__ == '__main__':
    import doctest
    fail, total = doctest.testmod()
    if not fail:
        print "%d tests passed." % total
