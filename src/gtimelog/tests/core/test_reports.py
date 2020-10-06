import doctest
import textwrap
import unittest
import sys
from datetime import datetime, date
from io import StringIO

import freezegun

from gtimelog.core.reports import Reports, ReportRecord
from gtimelog.core.utils import report_categories
from gtimelog.tests.commons import Checker, Mixins
from gtimelog.tests.core import make_time_window


def doctest_reports_weekly_report_categorized():
    r"""Tests for Reports.weekly_report_categorized

        >>> from datetime import datetime

        >>> minimum = datetime(2010, 1, 25)
        >>> maximum = datetime(2010, 1, 31)

        >>> window = make_time_window(minimum=minimum, maximum=maximum)
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

        >>> window = make_time_window(fh, minimum, maximum)
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


def doctest_reports_monthly_report_categorized():
    r"""Tests for Reports.monthly_report_categorized

        >>> from datetime import datetime, time

        >>> vm = time(2, 0)
        >>> minimum = datetime(2010, 1, 25)
        >>> maximum = datetime(2010, 1, 31)

        >>> window = make_time_window(minimum=minimum, maximum=maximum)
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

        >>> window = make_time_window(fh, minimum, maximum, vm)
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


def doctest_reports_report_categories():
    r"""Tests for Reports._report_categories

        >>> from datetime import datetime, time, timedelta

        >>> vm = time(2, 0)
        >>> minimum = datetime(2010, 1, 25)
        >>> maximum = datetime(2010, 1, 31)

        >>> categories = {
        ...    'Bing': timedelta(2),
        ...    None: timedelta(1)}

        >>> window = make_time_window(StringIO(), minimum, maximum, vm)
        >>> reports = Reports(window)
        >>> report_categories(sys.stdout, categories)
        <BLANKLINE>
        By category:
        <BLANKLINE>
        Bing                                                            48 hours
        (none)                                                          24 hours
        <BLANKLINE>

    """


def doctest_reports_daily_report():
    r"""Tests for Reports.daily_report

        >>> from datetime import datetime, time

        >>> vm = time(2, 0)
        >>> minimum = datetime(2010, 1, 30)
        >>> maximum = datetime(2010, 1, 31)

        >>> window = make_time_window(StringIO(), minimum, maximum, vm)
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

        >>> window = make_time_window(fh, minimum, maximum, vm)
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


def doctest_reports_weekly_report_plain():
    r"""Tests for Reports.weekly_report_plain

        >>> from datetime import datetime, time

        >>> vm = time(2, 0)
        >>> minimum = datetime(2010, 1, 25)
        >>> maximum = datetime(2010, 1, 31)

        >>> window = make_time_window(StringIO(), minimum, maximum, vm)
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

        >>> window = make_time_window(fh, minimum, maximum, vm)
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


def doctest_reports_monthly_report_plain():
    r"""Tests for Reports.monthly_report_plain

        >>> from datetime import datetime, time

        >>> vm = time(2, 0)
        >>> minimum = datetime(2007, 9, 1)
        >>> maximum = datetime(2007, 10, 1)

        >>> window = make_time_window(StringIO(), minimum, maximum, vm)
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

        >>> window = make_time_window(fh, minimum, maximum, vm)
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


def doctest_reports_custom_range_report_categorized():
    r"""Tests for Reports.custom_range_report_categorized

        >>> from datetime import datetime, time

        >>> vm = time(2, 0)
        >>> minimum = datetime(2010, 1, 25)
        >>> maximum = datetime(2010, 2, 1)

        >>> window = make_time_window(StringIO(), minimum, maximum, vm)
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

        >>> window = make_time_window(fh, minimum, maximum, vm)
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
            get_id(ReportRecord.WEEKLY, date(2016, 1, 1)),
            '2015/53',
        )

    @freezegun.freeze_time("2016-01-08 09:34:50")
    def test_record(self):
        rr = ReportRecord(self.filename)
        rr.record(rr.DAILY, date(2016, 1, 6), 'test@example.com')
        rr.record(rr.WEEKLY, date(2016, 1, 6), 'test@example.com')
        rr.record(rr.MONTHLY, date(2016, 1, 6), 'test@example.com')
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
            rr.get_recipients(rr.DAILY, date(2016, 1, 6)),
            [],
        )
        self.assertEqual(
            rr.get_recipients(rr.DAILY, date(2015, 12, 21)),
            [
                "test@example.com",
                "marius+test@example.com",
                "marius+test@example.com",
            ],
        )
        self.assertEqual(
            rr.get_recipients(rr.WEEKLY, date(2015, 12, 21)),
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
        now = datetime(2016, 1, 8, 9, 34, 50)
        rr.record(rr.DAILY, date(2016, 1, 6), 'test@example.com', now)
        self.assertEqual(
            rr.get_recipients(rr.DAILY, date(2016, 1, 6)),
            ['test@example.com']
        )

    def test_record_then_load_twice_when_empty(self):
        # Recording twice might not change the mtime because the resolution
        # is too low; so record() must update the internal data structures
        # by itself.
        rr = ReportRecord(self.filename)
        now = datetime(2016, 1, 8, 9, 34, 50)
        rr.record(rr.DAILY, date(2016, 1, 6), 'test@example.com', now)
        self.assertEqual(
            rr.get_recipients(rr.DAILY, date(2016, 1, 6)),
            ['test@example.com']
        )
        rr.record(rr.DAILY, date(2016, 1, 6), 'test@example.org', now)
        self.assertEqual(
            rr.get_recipients(rr.DAILY, date(2016, 1, 6)),
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
        now = datetime(2016, 1, 8, 9, 34, 50)
        rr.record(rr.DAILY, date(2016, 1, 6), 'test@example.org', now)
        self.assertEqual(
            rr.get_recipients(rr.DAILY, date(2016, 1, 6)),
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
        now = datetime(2016, 1, 8, 9, 34, 50)
        rr.record(rr.DAILY, date(2016, 1, 6), 'test@example.org', now)
        rr.record(rr.DAILY, date(2016, 1, 6), 'test@example.net', now)
        self.assertEqual(
            rr.get_recipients(rr.DAILY, date(2016, 1, 6)),
            ['test@example.com', 'test@example.org', 'test@example.net']
        )

    def test_automatic_reload(self):
        rr = ReportRecord(self.filename)
        self.assertEqual(
            rr.get_recipients(rr.DAILY, date(2016, 1, 6)),
            []
        )
        self.load_fixture([
            "2016-01-08 09:34:50,daily,2016-01-06,test@example.com",
            "2016-01-08 09:34:50,weekly,2016/1,test@example.com",
            "2016-01-08 09:34:50,monthly,2016-01,test@example.com",
        ])
        self.assertEqual(
            rr.get_recipients(rr.DAILY, date(2016, 1, 6)),
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
