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


if __name__ == '__main__':
    import doctest
    fail, total = doctest.testmod()
    if not fail:
        print "%d tests passed." % total
