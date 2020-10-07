"""Tests for gtimelog"""
import unittest

from gtimelog.tests.core import (
    test_exports,
    test_report_record,
    test_reports,
    test_settings,
    test_time,
    test_utils,
)
from gtimelog.tests.modules import test_email


def test_suite():
    return unittest.TestSuite([
        test_utils.test_suite(),
        test_settings.test_suite(),
        test_time.test_suite(),
        test_report_record.test_suite(),
        test_reports.test_suite(),
        test_exports.test_suite(),
        test_email.test_suite(),
    ])


def main():
    unittest.main(module='gtimelog.tests', defaultTest='test_suite')

