import doctest
import sys
import textwrap
import unittest
from datetime import datetime, time, timedelta
from io import StringIO

from gtimelog.core.reports import Reports
from gtimelog.core.utils import report_categories
from gtimelog.tests.core import make_time_window


def doctest_reports_weekly_report_categorized():
    r"""Tests for Reports.weekly_report_categorized

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


class TestReport(unittest.TestCase):
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
            datetime(2014, 5, 27, 9, 0),
            datetime(2014, 5, 27, 23, 59),
            time(2, 0),
        )

    def test_report_tags(self):
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

    def test_daily_report_includes_tags(self):
        rp = Reports(self.tw)
        txt = StringIO()
        rp.daily_report(txt, 'me@example.com', 'me')
        self.assertIn('Time spent in each area', txt.getvalue())

    def test_weekly_report_includes_tags(self):
        rp = Reports(self.tw)
        txt = StringIO()
        rp.weekly_report(txt, 'me@example.com', 'me')
        self.assertIn('Time spent in each area', txt.getvalue())

    def test_monthly_report_includes_tags(self):
        rp = Reports(self.tw)
        txt = StringIO()
        rp.monthly_report(txt, 'me@example.com', 'me')
        self.assertIn('Time spent in each area', txt.getvalue())

    def test_categorized_report_includes_tags(self):
        rp = Reports(self.tw, style='categorized')
        txt = StringIO()
        rp.weekly_report(txt, 'me@example.com', 'me')
        self.assertIn('Time spent in each area', txt.getvalue())
        txt = StringIO()
        rp.monthly_report(txt, 'me@example.com', 'me')
        self.assertIn('Time spent in each area', txt.getvalue())


def test_suite():
    return doctest.DocTestSuite(__name__, optionflags=doctest.NORMALIZE_WHITESPACE)
