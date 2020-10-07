import unittest
import sys
from datetime import datetime, time
from io import StringIO

import freezegun
from unittest import mock

from gtimelog.core.exports import Exports
from gtimelog.tests.core import make_time_window


def doctest_exports_to_csv_complete():
    r"""Tests for Exports.to_csv_complete

        >>> minimum = datetime(2008, 6, 1)
        >>> maximum = datetime(2008, 7, 1)
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

        >>> window = make_time_window(sampledata, minimum, maximum, vm)

        >>> Exports(window).to_csv_complete(sys.stdout)
        task,time (minutes)
        etc,60
        something,45
        something else,105

    """


def doctest_exports_to_csv_daily():
    r"""Tests for Exports.to_csv_daily

        >>> minimum = datetime(2008, 6, 1)
        >>> maximum = datetime(2008, 7, 1)
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

        >>> window = make_time_window(sampledata, minimum, maximum, vm)

        >>> Exports(window).to_csv_daily(sys.stdout)
        date,day-start (hours),slacking (hours),work (hours)
        2008-06-03,12.75,0.0,3.0
        2008-06-04,0.0,0.0,0.0
        2008-06-05,12.75,1.0,0.5

    """


def doctest_exports_icalendar():
    r"""Tests for Exports.icalendar

        >>> minimum = datetime(2008, 6, 1)
        >>> maximum = datetime(2008, 7, 1)
        >>> vm = time(2, 0)

        >>> sampledata = StringIO(r'''
        ... 2008-06-03 12:45: start **
        ... 2008-06-03 13:00: something
        ... 2008-06-03 15:45: something, else; with special\chars
        ... 2008-06-05 12:45: start **
        ... 2008-06-05 13:15: something
        ... 2008-06-05 14:15: rest **
        ... ''')

        >>> window = make_time_window(sampledata, minimum, maximum, vm)

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


def test_suite():
    return unittest.defaultTestLoader.loadTestsFromName(__name__)
