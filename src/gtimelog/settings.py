"""
Settings for GTimeLog
"""

import datetime
import locale
import os

try:
    from configparser import RawConfigParser
    PY3 = True
except ImportError:
    from ConfigParser import RawConfigParser
    PY3 = False


from gtimelog.timelog import parse_time


legacy_default_home = os.path.normpath('~/.gtimelog')
default_config_home = os.path.normpath('~/.config')
default_data_home = os.path.normpath('~/.local/share')


class Settings(object):
    """Configurable settings for GTimeLog."""

    # Apparently locale.getpreferredencoding() might be blank on Mac OS X
    _encoding = locale.getpreferredencoding() or 'UTF-8'

    # Insane defaults
    email = 'activity-list@example.com'
    name = 'Anonymous'

    editor = 'xdg-open'
    mailer = 'x-terminal-emulator -e "mutt -H %s"'
    spreadsheet = 'xdg-open %s'
    chronological = True
    summary_view = False
    show_tasks = True

    enable_gtk_completion = True  # False enables gvim-style completion

    hours = 8
    virtual_midnight = datetime.time(2, 0)

    task_list_url = ''
    edit_task_list_cmd = ''

    show_office_hours = True
    show_tray_icon = True
    prefer_app_indicator = True
    prefer_old_tray_icon = False
    start_in_tray = False

    report_style = 'plain'

    def check_legacy_config(self):
        envar_home = os.environ.get('GTIMELOG_HOME')
        if envar_home is not None:
            return os.path.expanduser(envar_home)
        if os.path.isdir(os.path.expanduser(legacy_default_home)):
            return os.path.expanduser(legacy_default_home)
        return None

    # http://standards.freedesktop.org/basedir-spec/basedir-spec-latest.html

    def get_config_dir(self):
        legacy = self.check_legacy_config()
        if legacy:
            return legacy
        xdg = os.environ.get('XDG_CONFIG_HOME') or default_config_home
        return os.path.join(os.path.expanduser(xdg), 'gtimelog')

    def get_data_dir(self):
        legacy = self.check_legacy_config()
        if legacy:
            return legacy
        xdg = os.environ.get('XDG_DATA_HOME') or default_data_home
        return os.path.join(os.path.expanduser(xdg), 'gtimelog')

    def get_config_file(self):
        return os.path.join(self.get_config_dir(), 'gtimelogrc')

    def get_timelog_file(self):
        return os.path.join(self.get_data_dir(), 'timelog.txt')

    def _config(self):
        config = RawConfigParser()
        config.add_section('gtimelog')
        config.set('gtimelog', 'list-email', self.email)
        config.set('gtimelog', 'name', self.name.encode(self._encoding))
        config.set('gtimelog', 'editor', self.editor)
        config.set('gtimelog', 'mailer', self.mailer)
        config.set('gtimelog', 'spreadsheet', self.spreadsheet)
        config.set('gtimelog', 'chronological', str(self.chronological))
        config.set('gtimelog', 'summary_view', str(self.summary_view))
        config.set('gtimelog', 'show_tasks', str(self.show_tasks))
        config.set('gtimelog', 'gtk-completion',
                   str(self.enable_gtk_completion))
        config.set('gtimelog', 'hours', str(self.hours))
        config.set('gtimelog', 'virtual_midnight',
                   self.virtual_midnight.strftime('%H:%M'))
        config.set('gtimelog', 'task_list_url', self.task_list_url)
        config.set('gtimelog', 'edit_task_list_cmd', self.edit_task_list_cmd)
        config.set('gtimelog', 'show_office_hours',
                   str(self.show_office_hours))
        config.set('gtimelog', 'show_tray_icon', str(self.show_tray_icon))
        config.set('gtimelog', 'prefer_app_indicator',
                   str(self.prefer_app_indicator))
        config.set('gtimelog', 'prefer_old_tray_icon',
                   str(self.prefer_old_tray_icon))
        config.set('gtimelog', 'report_style', str(self.report_style))
        config.set('gtimelog', 'start_in_tray', str(self.start_in_tray))
        return config

    if PY3:
        def _unicode(self, value):
            return value  # ConfigParser already gives us unicode
    else:
        def _unicode(self, value):
            return value.decode(self._encoding)

    def load(self, filename):
        config = self._config()
        config.read([filename])
        self.email = config.get('gtimelog', 'list-email')
        self.name = self._unicode(config.get('gtimelog', 'name'))
        self.editor = config.get('gtimelog', 'editor')
        self.mailer = config.get('gtimelog', 'mailer')
        self.spreadsheet = config.get('gtimelog', 'spreadsheet')
        self.chronological = config.getboolean('gtimelog', 'chronological')
        self.summary_view = config.getboolean('gtimelog', 'summary_view')
        self.show_tasks = config.getboolean('gtimelog', 'show_tasks')
        self.enable_gtk_completion = config.getboolean('gtimelog',
                                                       'gtk-completion')
        self.hours = config.getfloat('gtimelog', 'hours')
        self.virtual_midnight = parse_time(config.get('gtimelog',
                                                      'virtual_midnight'))
        self.task_list_url = config.get('gtimelog', 'task_list_url')
        self.edit_task_list_cmd = config.get('gtimelog', 'edit_task_list_cmd')
        self.show_office_hours = config.getboolean('gtimelog',
                                                   'show_office_hours')
        self.show_tray_icon = config.getboolean('gtimelog', 'show_tray_icon')
        self.prefer_app_indicator = config.getboolean('gtimelog',
                                                      'prefer_app_indicator')
        self.prefer_old_tray_icon = config.getboolean('gtimelog',
                                                      'prefer_old_tray_icon')
        self.report_style = config.get('gtimelog', 'report_style')
        self.start_in_tray = config.getboolean('gtimelog', 'start_in_tray')

    def save(self, filename):
        config = self._config()
        with open(filename, 'w') as f:
            config.write(f)

