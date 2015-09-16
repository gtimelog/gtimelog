# -*- coding: utf-8 -*-
"""Tests for gtimelog.main"""

import textwrap
import unittest

import mock


gi = mock.MagicMock()
gi.repository.Gtk.MAJOR_VERSION = 3
gi.repository.Gtk.MINOR_VERSION = 16
mock_gi = mock.patch.dict('sys.modules', {'gi': gi, 'gi.repository': gi.repository})


@mock_gi
class TestEmail(unittest.TestCase):

    def test_message_from_string_ascii(self):
        from gtimelog.main import message_from_string
        msg = message_from_string(textwrap.dedent('''\
            From: ASCII Name <test@example.com>
            To: activity@example.com
            Subject: Report for Mr. Plain

            These are the activites done by Mr. Plain:
            ...
        '''))
        self.assertEqual("ASCII Name <test@example.com>", msg["From"])
        self.assertEqual("activity@example.com", msg["To"])
        self.assertEqual("Report for Mr. Plain", msg["Subject"])
        expected = textwrap.dedent('''\
            From: ASCII Name <test@example.com>
            To: activity@example.com
            Subject: Report for Mr. Plain

            These are the activites done by Mr. Plain:
            ...
        ''')
        self.assertEqual(expected, msg.as_string())

    def test_message_from_string_unicode(self):
        from gtimelog.main import message_from_string
        msg = message_from_string(textwrap.dedent('''\
            From: Ünicødę Name <test@example.com>
            To: Anöther nąme <activity@example.com>
            Subject: Report for Mr. ☃

            These are the activites done by Mr. ☃:
            ...
        '''))
        expected = textwrap.dedent('''\
            From: =?utf-8?b?w5xuaWPDuGTEmSBOYW1l?= <test@example.com>
            To: =?utf-8?b?QW7DtnRoZXIgbsSFbWU=?= <activity@example.com>
            Subject: =?utf-8?b?UmVwb3J0IGZvciBNci4g4piD?=

            These are the activites done by Mr. ☃:
            ...
        ''')
        self.assertEqual(expected, msg.as_string())


def test_suite():
    return unittest.defaultTestLoader.loadTestsFromName(__name__)
