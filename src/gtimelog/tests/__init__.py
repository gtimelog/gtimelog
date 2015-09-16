"""Tests for gtimelog"""
import unittest

from gtimelog.tests import test_timelog, test_settings


def test_suite():
    return unittest.TestSuite([
        test_timelog.test_suite(),
        test_settings.test_suite(),
    ])


def main():
    unittest.main(module='gtimelog.tests', defaultTest='test_suite')
