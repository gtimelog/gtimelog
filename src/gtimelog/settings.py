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

    _encoding = locale.getpreferredencoding()

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
    """If True then timestamp of the event will be present in categorized report"""
    report_categorized_withdate = False
    
    """If True then treat categories with 'subcategories_separator' as multi-level categories"""
    subcategories_enabled = False
    """Separator for levels in multi-level categories"""
    subcategories_separator = '_'
    
    timelog_filename = None
    timelog_filename_def = 'timelog.txt'
    config_filename = None
    config_filename_def = 'gtimelogrc'
    

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

    def set_config_file(self, filename = None):
        """Setter mainly for testing purposes.
        
        Set filename if not set or if filename is provided"""
        if (self.config_filename is None) or (filename is not None):
            if filename is None:
                self.config_filename = os.path.join(self.get_config_dir(), self.config_filename_def)
            else:
                self.config_filename = filename
                
    def get_config_file(self):
        if self.config_filename is None:
            self.set_config_file()
        return self.config_filename

    def set_timelog_file(self, filename = None):
        """Setter mainly for testing purposes.
        
        Set filename if not set or if filename is provided"""
        if (self.timelog_filename is None) or (filename is not None):
            if filename is None:
                self.timelog_filename = os.path.join(self.get_data_dir(), self.timelog_filename_def)
            else:
                self.timelog_filename = filename

    def get_timelog_file(self):
        if self.timelog_filename is None:
            self.set_timelog_file()
        return self.timelog_filename

    def set_subcategories_separator(self, separator):
        self.subcategories_separator = separator[0]
    
    def set_enable_subcategories(self, enable):
            self.subcategories_enabled = enable

    def set_enable_report_categorized_withdate(self, enable):
            self.report_categorized_withdate = enable

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
        config.set('gtimelog', 'report_categorized_withdate', 
                   str(self.report_categorized_withdate))
        config.set('gtimelog', 'start_in_tray', str(self.start_in_tray))
        config.set('gtimelog', 'subcategories_enabled', 
                   str(self.subcategories_enabled))
        config.set('gtimelog', 'subcategories_separator', 
                   self.set_subcategories_separator( 
                       str(self.subcategories_separator)))
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
        self.report_categorized_withdate = config.getboolean('gtimelog', 
                                                             'report_categorized_withdate')
        self.start_in_tray = config.getboolean('gtimelog', 'start_in_tray')
        self.subcategories_enabled = config.getboolean('gtimelog', 
                                                'subcategories_enabled' ) 
        self.subcategories_separator = config.get('gtimelog', 
                                                  'subcategories_separator') 

    def save(self, filename):
        config = self._config()
        with open(filename, 'w') as f:
            config.write(f)

