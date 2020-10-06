"""Tests for gtimelog"""
import unittest

from gtimelog.tests.core import test_utils as test_utils_core, test_reports, test_timelog, \
    test_settings
from gtimelog.tests.components import test_utils as test_utils_component
from gtimelog.tests.modules import test_email


def test_suite():
    return unittest.TestSuite([
        test_utils_core.test_suite(),
        test_utils_component.test_suite(),
        test_settings.test_suite(),
        test_timelog.test_suite(),
        test_reports.test_suite(),
        test_email.test_suite(),
    ])


def main():
    unittest.main(module='gtimelog.tests', defaultTest='test_suite')

