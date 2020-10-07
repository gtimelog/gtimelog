import doctest
import os
import textwrap
import unittest
from datetime import date, datetime, time, timedelta
from io import StringIO

import freezegun

from gtimelog.core.time import TimeCollection, TimeLog
from gtimelog.tests.commons import Mixins
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
    # FIX: datetime.datetime
    # As python 3.7 and 3.8 doesn't send the same representation
    # for duration : using seconds instead of __repr__
    # python3.7 result : datetime.timedelta(0, 1860)
    # python3.8 result : datetime.timedelta(seconds=1860)

        >>> window.items = [
        ...     (datetime(2013, 12, 4, 9, 0), 'started **'),
        ...     (datetime(2013, 12, 4, 9, 31), 'gtimelog: tests'),
        ... ]
        >>> start, stop, duration, tags, entry = window.last_entry()
        >>> start
        datetime.datetime(2013, 12, 4, 9, 0)
        >>> stop
        datetime.datetime(2013, 12, 4, 9, 31)
        >>> duration.seconds
        1860
        >>> entry
        'gtimelog: tests'

    """


class TestTimeCollection(unittest.TestCase):

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


class TestTimeLog(Mixins, unittest.TestCase):

    def test_reloading(self):
        logfile = self.tempfile()
        timelog = TimeLog(logfile, time(2, 0))
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
        timelog = TimeLog(StringIO(), time(2, 0))
        window = timelog.window_for_day(date(2015, 9, 17))
        self.assertEqual(window.min_timestamp, datetime(2015, 9, 17, 2, 0))
        self.assertEqual(window.max_timestamp, datetime(2015, 9, 18, 2, 0))

    def test_window_for_week(self):
        timelog = TimeLog(StringIO(), time(2, 0))
        for d in range(14, 21):
            window = timelog.window_for_week(date(2015, 9, d))
            self.assertEqual(window.min_timestamp, datetime(2015, 9, 14, 2, 0))
            self.assertEqual(window.max_timestamp, datetime(2015, 9, 21, 2, 0))

    def test_window_for_month(self):
        timelog = TimeLog(StringIO(), time(2, 0))
        for d in range(1, 31):
            window = timelog.window_for_month(date(2015, 9, d))
            self.assertEqual(window.min_timestamp, datetime(2015, 9, 1, 2, 0))
            self.assertEqual(window.max_timestamp, datetime(2015, 10, 1, 2, 0))

    def test_window_for_date_range(self):
        timelog = TimeLog(StringIO(), time(2, 0))
        window = timelog.window_for_date_range(date(2015, 9, 3),
                                               date(2015, 9, 24))
        self.assertEqual(window.min_timestamp, datetime(2015, 9, 3, 2, 0))
        self.assertEqual(window.max_timestamp, datetime(2015, 9, 25, 2, 0))

    def test_appending_clears_window_cache(self):
        # Regression test for https://github.com/gtimelog/gtimelog/issues/28
        timelog = TimeLog(self.tempfile(), time(2, 0))

        w = timelog.window_for_day(date(2014, 11, 12))
        self.assertEqual(list(w.all_entries()), [])

        timelog.append('started **', now=datetime(2014, 11, 12, 10, 00))
        w = timelog.window_for_day(date(2014, 11, 12))
        self.assertEqual(len(list(w.all_entries())), 1)

    def test_append_adds_blank_line_on_new_day(self):
        timelog = TimeLog(self.tempfile(), time(2, 0))
        timelog.append('working on sth', now=datetime(2014, 11, 12, 18, 0))
        timelog.append('new day **', now=datetime(2014, 11, 13, 8, 0))
        with open(timelog.filename, 'r') as f:
            self.assertEqual(f.readlines(),
                             ['2014-11-12 18:00: working on sth\n',
                              '\n',
                              '2014-11-13 08:00: new day **\n'])

    @freezegun.freeze_time("2015-05-12 16:27:35.115265")
    def test_append_rounds_the_time(self):
        timelog = TimeLog(self.tempfile(), time(2, 0))
        timelog.append('now')
        self.assertEqual(timelog.items[-1][0], datetime(2015, 5, 12, 16, 27))

    @freezegun.freeze_time("2015-05-12 16:27")
    def test_valid_time_accepts_any_time_in_the_past_when_log_is_empty(self):
        timelog = TimeLog(StringIO(), time(2, 0))
        past = datetime(2015, 5, 12, 14, 20)
        self.assertTrue(timelog.valid_time(past))

    @freezegun.freeze_time("2015-05-12 16:27")
    def test_valid_time_rejects_times_in_the_future(self):
        timelog = TimeLog(StringIO(), time(2, 0))
        future = datetime(2015, 5, 12, 16, 30)
        self.assertFalse(timelog.valid_time(future))

    @freezegun.freeze_time("2015-05-12 16:27")
    def test_valid_time_rejects_times_before_last_entry(self):
        timelog = TimeLog(StringIO("2015-05-12 15:00: did stuff"),
                          time(2, 0))
        past = datetime(2015, 5, 12, 14, 20)
        self.assertFalse(timelog.valid_time(past))

    @freezegun.freeze_time("2015-05-12 16:27")
    def test_valid_time_accepts_times_between_last_entry_and_now(self):
        timelog = TimeLog(StringIO("2015-05-12 15:00: did stuff"),
                          time(2, 0))
        past = datetime(2015, 5, 12, 15, 20)
        self.assertTrue(timelog.valid_time(past))

    def test_parse_correction_leaves_regular_text_alone(self):
        timelog = TimeLog(StringIO(), time(2, 0))
        self.assertEqual(timelog.parse_correction("did stuff"),
                         ("did stuff", None))

    @freezegun.freeze_time("2015-05-12 16:27")
    def test_parse_correction_recognizes_absolute_times(self):
        timelog = TimeLog(StringIO(), time(2, 0))
        self.assertEqual(timelog.parse_correction("15:20 did stuff"),
                         ("did stuff", datetime(2015, 5, 12, 15, 20)))

    @freezegun.freeze_time("2015-05-13 00:27")
    def test_parse_correction_handles_virtual_midnight_yesterdays_time(self):
        # Regression test for https://github.com/gtimelog/gtimelog/issues/33
        timelog = TimeLog(StringIO(), time(2, 0))
        self.assertEqual(timelog.parse_correction("15:20 did stuff"),
                         ("did stuff", datetime(2015, 5, 12, 15, 20)))

    @freezegun.freeze_time("2015-05-13 00:27")
    def test_parse_correction_handles_virtual_midnight_todays_time(self):
        timelog = TimeLog(StringIO(), time(2, 0))
        self.assertEqual(timelog.parse_correction("00:15 did stuff"),
                         ("did stuff", datetime(2015, 5, 13, 00, 15)))

    @freezegun.freeze_time("2015-05-12 16:27")
    def test_parse_correction_ignores_future_absolute_times(self):
        timelog = TimeLog(StringIO(), time(2, 0))
        self.assertEqual(timelog.parse_correction("17:20 did stuff"),
                         ("17:20 did stuff", None))

    @freezegun.freeze_time("2015-05-12 16:27")
    def test_parse_correction_ignores_bad_absolute_times(self):
        timelog = TimeLog(StringIO(), time(2, 0))
        self.assertEqual(timelog.parse_correction("19:60 did stuff"),
                         ("19:60 did stuff", None))
        self.assertEqual(timelog.parse_correction("24:00 did stuff"),
                         ("24:00 did stuff", None))

    @freezegun.freeze_time("2015-05-12 16:27")
    def test_parse_correction_ignores_absolute_times_before_last_entry(self):
        timelog = TimeLog(StringIO("2015-05-12 16:00: stuff"),
                          time(2, 0))
        self.assertEqual(timelog.parse_correction("15:20 did stuff"),
                         ("15:20 did stuff", None))

    @freezegun.freeze_time("2015-05-12 16:27")
    def test_parse_correction_recognizes_relative_times(self):
        timelog = TimeLog(StringIO(), time(2, 0))
        self.assertEqual(timelog.parse_correction("-20 did stuff"),
                         ("did stuff", datetime(2015, 5, 12, 16, 7)))

    @freezegun.freeze_time("2015-05-12 16:27")
    def test_parse_correction_ignores_relative_times_before_last_entry(self):
        timelog = TimeLog(StringIO("2015-05-12 16:00: stuff"),
                          time(2, 0))
        self.assertEqual(timelog.parse_correction("-30 did stuff"),
                         ("-30 did stuff", None))

    @freezegun.freeze_time("2015-05-12 16:27")
    def test_parse_correction_ignores_bad_relative_times(self):
        timelog = TimeLog(StringIO(), time(2, 0))
        self.assertEqual(timelog.parse_correction("-200 did stuff"),
                         ("-200 did stuff", None))


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
            datetime(2018, 12, 9, 8, 0),
            datetime(2018, 12, 9, 23, 59),
            time(2, 0),
        )

    def test_totals(self):
        work, slack = self.tw.totals()
        self.assertEqual(work, timedelta(hours=3, minutes=10))
        self.assertEqual(slack, timedelta(hours=0, minutes=5))


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
            datetime(2014, 5, 27, 9, 0),
            datetime(2014, 5, 27, 23, 59),
            time(2, 0),
        )

    def test_totals_filtering1(self):
        work, slack = self.tw.totals(filter_text='support')
        # matches two items: 1h 41m (10:30--12:11) + 11m (17:03--17:14)
        self.assertEqual(work, timedelta(hours=1, minutes=52))
        self.assertEqual(slack, timedelta(0))

    def test_totals_filtering2(self):
        work, slack = self.tw.totals(filter_text='f')
        # matches four items:
        # 3h  1m (12:11--15:12) edx: write test procedure [f]or EdX instances
        # 3h 13m (19:06--22:19) cluster: [f]ix shmmax-shmall issue
        # total work: 6h 14m
        #    22m (17:14--17:36) o[f]f: pause **
        # 1h 28m (17:38--19:06) o[f]f: dinner & family **
        # total slacking: 1h 50m
        self.assertEqual(work, timedelta(hours=6, minutes=14))
        self.assertEqual(slack, timedelta(hours=1, minutes=50))


class TestTimeWindow(unittest.TestCase):
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

    def test_set_of_all_tags(self):
        tags = self.tw.set_of_all_tags()
        self.assertEqual(tags, {
            'edx', 'hpc', 'hydra', 'meeting', 'support', 'sysadmin'
        })

    def test_totals_per_tag1(self):
        """Test aggregate time per tag, 1 entry only"""
        result = self.tw.totals('meeting')
        self.assertEqual(len(result), 2)
        work, slack = result
        self.assertEqual(
            work,
            # start/end times are manually extracted from the TEST_TIMELOG sample
            (timedelta(hours=12, minutes=11) - timedelta(hours=10, minutes=30))
        )
        self.assertEqual(slack, timedelta(0))

    def test_totals_per_tag2(self):
        """Test aggregate time per tag, several entries"""
        result = self.tw.totals('hpc')
        self.assertEqual(len(result), 2)
        work, slack = result
        self.assertEqual(
            work,
            # start/end times are manually extracted from the TEST_TIMELOG sample
            (timedelta(hours=17, minutes=3) - timedelta(hours=15, minutes=12))
            + (timedelta(hours=22, minutes=19) - timedelta(hours=19, minutes=6))
        )
        self.assertEqual(slack, timedelta(0))

    def test_split_entry_and_tags1(self):
        """Test `TimeWindow._split_entry_and_tags` with simple entry"""
        result = self.tw._split_entry_and_tags('email')
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], 'email')
        self.assertEqual(result[1], set())

    def test_split_entry_and_tags2(self):
        """Test `TimeWindow._split_entry_and_tags` with simple entry and tags"""
        result = self.tw._split_entry_and_tags('restart CFEngine server -- sysadmin cfengine issue327')
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], 'restart CFEngine server')
        self.assertEqual(result[1], {'sysadmin', 'cfengine', 'issue327'})

    def test_split_entry_and_tags3(self):
        """Test `TimeWindow._split_entry_and_tags` with category, entry, and tags"""
        result = self.tw._split_entry_and_tags('tooling: tagging support in gtimelog -- tooling gtimelog')
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], 'tooling: tagging support in gtimelog')
        self.assertEqual(result[1], {'tooling', 'gtimelog'})

    def test_split_entry_and_tags4(self):
        """Test `TimeWindow._split_entry_and_tags` with slack-type entry"""
        result = self.tw._split_entry_and_tags('read news -- reading **')
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], 'read news **')
        self.assertEqual(result[1], {'reading'})

    def test_split_entry_and_tags5(self):
        """Test `TimeWindow._split_entry_and_tags` with slack-type entry"""
        result = self.tw._split_entry_and_tags('read news -- reading ***')
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], 'read news ***')
        self.assertEqual(result[1], {'reading'})


def test_suite():
    return unittest.TestSuite([
        unittest.defaultTestLoader.loadTestsFromTestCase(TestTotals),
        unittest.defaultTestLoader.loadTestsFromTestCase(TestFiltering),
        unittest.defaultTestLoader.loadTestsFromTestCase(TestTimeWindow),
        unittest.defaultTestLoader.loadTestsFromTestCase(TestTimeLog),
        unittest.defaultTestLoader.loadTestsFromTestCase(TestTimeCollection),
        doctest.DocTestSuite(__name__, optionflags=doctest.NORMALIZE_WHITESPACE)
    ])
