import unittest
from datetime import date, datetime

import freezegun

from gtimelog.core.reports import ReportRecord
from gtimelog.tests.commons import Mixins


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


def test_suite():
    return unittest.defaultTestLoader.loadTestsFromTestCase(TestReportRecord)
