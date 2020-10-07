"""Tests for gtimelog"""
import unittest

from gtimelog.tests import test_main, test_settings, test_timelog


def test_suite():
    return unittest.TestSuite([
        test_timelog.test_suite(),
        test_settings.test_suite(),
        test_main.test_suite(),
    ])


def main():
    unittest.main(module='gtimelog.tests', defaultTest='test_suite')
