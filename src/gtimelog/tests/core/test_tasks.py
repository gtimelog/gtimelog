import os
import textwrap
import time
import unittest

from gtimelog.core.tasks import TaskList
from gtimelog.tests.commons import Mixins


class TestTaskList(Mixins, unittest.TestCase):

    def test_missing_file(self):
        tasklist = TaskList('/nosuchfile')
        self.assertFalse(tasklist.check_reload())
        tasklist.reload()  # no crash

    def test_parsing(self):
        taskfile = self.write_file('tasks.txt', textwrap.dedent('''\
            # comments are skipped
            some task
            other task
            project: do it
            project: fix bugs
            misc: paperwork
        '''))
        tasklist = TaskList(taskfile)
        self.assertEqual(tasklist.groups, [
            ('Other', ['some task', 'other task']),
            ('misc', ['paperwork']),
            ('project', ['do it', 'fix bugs']),
        ])

    def test_unicode(self):
        taskfile = self.write_file('tasks.txt', u'\N{SNOWMAN}')
        tasklist = TaskList(taskfile)
        self.assertEqual(tasklist.groups, [
            ('Other', [u'\N{SNOWMAN}']),
        ])

    def test_reloading(self):
        taskfile = self.write_file('tasks.txt', 'some tasks\n')
        couple_seconds_ago = time.time() - 2
        os.utime(taskfile, (couple_seconds_ago, couple_seconds_ago))

        tasklist = TaskList(taskfile)
        self.assertEqual(tasklist.groups, [
            ('Other', ['some tasks']),
        ])
        self.assertFalse(tasklist.check_reload())

        with open(taskfile, 'w') as f:
            f.write('new tasks\n')

        self.assertTrue(tasklist.check_reload())

        self.assertEqual(tasklist.groups, [
            ('Other', ['new tasks']),
        ])


def test_suite():
    return unittest.defaultTestLoader.loadTestsFromTestCase(TestTaskList)
