# -*- coding: utf-8 -*-
"""Tests for gtimelog.main"""

import textwrap
import unittest

try:
    # Python 3
    from unittest import mock
except ImportError:
    # Python 2
    import mock


gi = mock.MagicMock()
gi.repository.Gtk.MAJOR_VERSION = 3
gi.repository.Gtk.MINOR_VERSION = 18
mock_gi = mock.patch.dict('sys.modules', {'gi': gi, 'gi.repository': gi.repository})


@mock_gi
class TestEmail(unittest.TestCase):

    def test_prepare_message_ascii(self):
        from gtimelog.main import prepare_message, __version__
        msg = prepare_message(
            sender='ASCII Name <test@example.com>',
            recipient='activity@example.com',
            subject='Report for Mr. Plain',
            body='These are the activites done by Mr. Plain:\n...\n',
        )
        self.assertEqual("ASCII Name <test@example.com>", msg["From"])
        self.assertEqual("activity@example.com", msg["To"])
        self.assertEqual("Report for Mr. Plain", msg["Subject"])
        expected = textwrap.dedent('''\
            Content-Type: text/plain; charset="us-ascii"
            MIME-Version: 1.0
            Content-Transfer-Encoding: 7bit
            From: ASCII Name <test@example.com>
            To: activity@example.com
            Subject: Report for Mr. Plain
            User-Agent: gtimelog/0.11.dev0

            These are the activites done by Mr. Plain:
            ...
        ''').replace('0.11.dev0', __version__)
        self.assertEqual(expected, msg.as_string())

    def test_prepare_message_unicode(self):
        from gtimelog.main import prepare_message, __version__
        msg = prepare_message(
            sender='Ünicødę Name <test@example.com>',
            recipient='Anöther nąme <activity@example.com>',
            subject='Report for Mr. ☃',
            body='These are the activites done by Mr. ☃:\n...\n',
        )
        expected = textwrap.dedent('''\
            MIME-Version: 1.0
            Content-Type: text/plain; charset="utf-8"
            Content-Transfer-Encoding: base64
            From: =?utf-8?b?w5xuaWPDuGTEmSBOYW1l?= <test@example.com>
            To: =?utf-8?b?QW7DtnRoZXIgbsSFbWU=?= <activity@example.com>
            Subject: =?utf-8?b?UmVwb3J0IGZvciBNci4g4piD?=
            User-Agent: gtimelog/0.11.dev0

            VGhlc2UgYXJlIHRoZSBhY3Rpdml0ZXMgZG9uZSBieSBNci4g4piDOgouLi4K
        ''').replace('0.11.dev0', __version__)
        self.assertEqual(expected, msg.as_string())


def test_suite():
    return unittest.defaultTestLoader.loadTestsFromName(__name__)
