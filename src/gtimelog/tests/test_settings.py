"""Tests for gtimelog.settings"""

import os
import shutil
import tempfile
import unittest

from gtimelog.settings import Settings


class TestSettings(unittest.TestCase):

    def setUp(self):
        self.settings = Settings()
        self.real_isdir = os.path.isdir
        self.tempdir = None
        self.old_home = os.environ.get('HOME')
        self.old_userprofile = os.environ.get('USERPROFILE')
        self.old_gtimelog_home = os.environ.get('GTIMELOG_HOME')
        self.old_xdg_config_home = os.environ.get('XDG_CONFIG_HOME')
        self.old_xdg_data_home = os.environ.get('XDG_DATA_HOME')
        os.environ['HOME'] = os.path.normpath('/tmp/home')
        os.environ['USERPROFILE'] = os.path.normpath('/tmp/home')
        os.environ.pop('GTIMELOG_HOME', None)
        os.environ.pop('XDG_CONFIG_HOME', None)
        os.environ.pop('XDG_DATA_HOME', None)

    def tearDown(self):
        os.path.isdir = self.real_isdir
        if self.tempdir:
            shutil.rmtree(self.tempdir)
        self.restore_env('HOME', self.old_home)
        self.restore_env('USERPROFILE', self.old_userprofile)
        self.restore_env('GTIMELOG_HOME', self.old_gtimelog_home)
        self.restore_env('XDG_CONFIG_HOME', self.old_xdg_config_home)
        self.restore_env('XDG_DATA_HOME', self.old_xdg_data_home)

    def restore_env(self, envvar, value):
        if value is not None:
            os.environ[envvar] = value
        else:
            os.environ.pop(envvar, None)

    def mkdtemp(self):
        if self.tempdir is None:
            self.tempdir = tempfile.mkdtemp(prefix='gtimelog-test-')
        return self.tempdir

    def test_get_config_dir_1(self):
        # Case 1: GTIMELOG_HOME is present in the environment
        os.environ['GTIMELOG_HOME'] = os.path.normpath('~/.gt')
        self.assertEqual(self.settings.get_config_dir(),
                         os.path.normpath('/tmp/home/.gt'))

    def test_get_config_dir_2(self):
        # Case 2: ~/.gtimelog exists
        os.path.isdir = lambda dir: True
        self.assertEqual(self.settings.get_config_dir(),
                         os.path.normpath('/tmp/home/.gtimelog'))

    def test_get_config_dir_3(self):
        # Case 3: ~/.gtimelog does not exist, so we use XDG
        os.path.isdir = lambda dir: False
        self.assertEqual(self.settings.get_config_dir(),
                         os.path.normpath('/tmp/home/.config/gtimelog'))

    def test_get_config_dir_4(self):
        # Case 4: XDG_CONFIG_HOME is present in the environment
        os.environ['XDG_CONFIG_HOME'] = os.path.normpath('~/.conf')
        self.assertEqual(self.settings.get_config_dir(),
                         os.path.normpath('/tmp/home/.conf/gtimelog'))

    def test_get_data_dir_1(self):
        # Case 1: GTIMELOG_HOME is present in the environment
        os.environ['GTIMELOG_HOME'] = os.path.normpath('~/.gt')
        self.assertEqual(self.settings.get_data_dir(),
                         os.path.normpath('/tmp/home/.gt'))

    def test_get_data_dir_2(self):
        # Case 2: ~/.gtimelog exists
        os.path.isdir = lambda dir: True
        self.assertEqual(self.settings.get_data_dir(),
                         os.path.normpath('/tmp/home/.gtimelog'))

    def test_get_data_dir_3(self):
        # Case 3: ~/.gtimelog does not exist, so we use XDG
        os.path.isdir = lambda dir: False
        self.assertEqual(self.settings.get_data_dir(),
                         os.path.normpath('/tmp/home/.local/share/gtimelog'))

    def test_get_data_dir_4(self):
        # Case 4: XDG_CONFIG_HOME is present in the environment
        os.environ['XDG_DATA_HOME'] = os.path.normpath('~/.data')
        self.assertEqual(self.settings.get_data_dir(),
                         os.path.normpath('/tmp/home/.data/gtimelog'))

    def test_get_config_file(self):
        self.settings.get_config_dir = lambda: os.path.normpath('~/.config/gtimelog')
        self.assertEqual(self.settings.get_config_file(),
                         os.path.normpath('~/.config/gtimelog/gtimelogrc'))

    def test_get_timelog_file(self):
        self.settings.get_data_dir = lambda: os.path.normpath('~/.local/share/gtimelog')
        self.assertEqual(self.settings.get_timelog_file(),
                         os.path.normpath('~/.local/share/gtimelog/timelog.txt'))

    def test_get_report_log_file(self):
        self.settings.get_data_dir = lambda: os.path.normpath('~/.local/share/gtimelog')
        self.assertEqual(self.settings.get_report_log_file(),
                         os.path.normpath('~/.local/share/gtimelog/sentreports.log'))

    def test_get_task_list_file(self):
        self.settings.get_data_dir = lambda: os.path.normpath('~/.local/share/gtimelog')
        self.assertEqual(self.settings.get_task_list_file(),
                         os.path.normpath('~/.local/share/gtimelog/tasks.txt'))

    def test_get_task_list_cache_file(self):
        self.settings.get_data_dir = lambda: os.path.normpath('~/.local/share/gtimelog')
        self.assertEqual(self.settings.get_task_list_cache_file(),
                         os.path.normpath('~/.local/share/gtimelog/remote-tasks.txt'))

    def test_load(self):
        self.settings.load('/dev/null')
        self.assertEqual(self.settings.name, 'Anonymous')

    def test_load_default_file(self):
        self.settings.load()

    def test_save(self):
        tempdir = self.mkdtemp()
        self.settings.save(os.path.join(tempdir, 'config'))


def test_suite():
    return unittest.defaultTestLoader.loadTestsFromName(__name__)
