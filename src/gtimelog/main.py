"""An application for keeping track of your time."""
import sys
import time


DEBUG = '--debug' in sys.argv


if DEBUG:
    def mark_time(what=None, _prev=[0, 0]):
        t = time.time()
        if what:
            print("{:.3f} ({:+.3f}) {}".format(t - _prev[1], t - _prev[0], what))
        else:
            print()
            _prev[1] = t
        _prev[0] = t
else:
    def mark_time(what=None):
        pass


mark_time()
mark_time("in script")

import collections
import datetime
import email
import email.header
import email.mime.text
import functools
import gettext
import locale
import logging
import os
import re
import signal
import smtplib
from contextlib import closing
from email.utils import formataddr, parseaddr
from gettext import gettext as _
from io import StringIO


mark_time("Python imports done")


if DEBUG:
    os.environ['G_ENABLE_DIAGNOSTIC'] = '1'


# The gtimelog.paths import has important side effects and must be done before
# importing 'gi'.

from .paths import (
    ABOUT_DIALOG_UI_FILE,
    CONTRIBUTORS_FILE,
    CSS_FILE,
    LOCALE_DIR,
    MENUS_UI_FILE,
    PREFERENCES_UI_FILE,
    SHORTCUTS_UI_FILE,
    UI_FILE,
)
from .utils import require_version


require_version('Gtk', '3.0')
require_version('Gdk', '3.0')
require_version('Soup', '3.0')
import gi
from gi.repository import Gdk, Gio, GLib, GObject, Gtk, Pango, Soup


mark_time("Gtk imports done")

from gtimelog import __version__
from gtimelog.secrets import (
    Authenticator,
    set_smtp_password,
    start_smtp_password_lookup,
)
from gtimelog.settings import Settings
from gtimelog.timelog import (
    ReportRecord,
    Reports,
    TaskList,
    TimeLog,
    as_minutes,
    different_days,
    next_month,
    parse_time,
    prev_month,
    uniq,
    virtual_day,
)


mark_time("gtimelog imports done")


log = logging.getLogger('gtimelog')


MailProtocol = collections.namedtuple('MailProtocol', 'factory, startssl')

MAIL_PROTOCOLS = {
    'SMTP': MailProtocol(smtplib.SMTP, False),
    'SMTPS': MailProtocol(smtplib.SMTP_SSL, False),
    'SMTP (StartTLS)': MailProtocol(smtplib.SMTP, True),
}


class EmailError(Exception):
    pass


def format_duration(duration):
    """Format a datetime.timedelta with minute precision.

    The difference from gtimelog.timelog.format_duration() is that this
    one is internationalized.
    """
    h, m = divmod(as_minutes(duration), 60)
    return _('{0} h {1} min').format(h, m)


def isascii(s):
    return all(0 <= ord(c) <= 127 for c in s)


def address_header(name_and_address):
    if isascii(name_and_address):
        return name_and_address
    name, addr = parseaddr(name_and_address)
    name = str(email.header.Header(name, 'UTF-8'))
    return formataddr((name, addr))


def subject_header(header):
    if isascii(header):
        return header
    return email.header.Header(header, 'UTF-8')


def prepare_message(sender, recipient, subject, body):
    if isascii(body):
        msg = email.mime.text.MIMEText(body)
    else:
        msg = email.mime.text.MIMEText(body, _charset="UTF-8")
    if sender:
        msg["From"] = address_header(sender)
    msg["To"] = address_header(recipient)
    msg["Subject"] = subject_header(subject)
    msg["User-Agent"] = "gtimelog/{}".format(__version__)
    return msg


def make_option(long_name, short_name=None, flags=0, arg=GLib.OptionArg.NONE,
                arg_data=None, description=None, arg_description=None):
    # surely something like this should exist inside PyGObject itself?!
    option = GLib.OptionEntry()
    option.long_name = long_name.lstrip('-')
    option.short_name = 0 if not short_name else short_name.lstrip('-')
    option.flags = flags
    # Not 100% sure about the int(), but it fixes a warning from PyGI
    option.arg = int(arg)
    option.arg_data = arg_data
    option.description = description
    option.arg_description = arg_description
    return option


soup_session = Soup.Session()
authenticator = Authenticator()


class Application(Gtk.Application):

    class Actions(object):

        actions = [
            'preferences',
            'shortcuts',
            'about',
            'quit',
            'edit-log',
            'edit-tasks',
            'refresh-tasks',
        ]

        def __init__(self, app):
            for action_name in self.actions:
                action = Gio.SimpleAction.new(action_name, None)
                action.connect('activate', getattr(app, 'on_' + action_name.replace('-', '_')))
                app.add_action(action)
                setattr(self, action_name.replace('-', '_'), action)

            self.shortcuts.set_enabled(hasattr(Gtk, 'ShortcutsWindow'))

    def __init__(self):
        super(Application, self).__init__(
            application_id='org.gtimelog',
            flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE,
        )
        GLib.set_application_name(_("Time Log"))
        GLib.set_prgname('gtimelog')
        self.add_main_option_entries([
            make_option("--version", description=_("Show version number and exit")),
            make_option("--debug", description=_("Show debug information on the console")),
            make_option("--prefs", description=_("Open the preferences dialog")),
            make_option("--email-prefs", description=_("Open the preferences dialog on the email page")),
        ])

    def check_schema(self):
        schema_source = Gio.SettingsSchemaSource.get_default()
        if schema_source.lookup("org.gtimelog", False) is None:
            sys.exit(_("\nWARNING: GSettings schema for org.gtimelog is missing!  If you're running from a source checkout, be sure to run 'make'."))

    def create_data_directory(self):
        data_dir = Settings().get_data_dir()
        if not os.path.exists(data_dir):
            try:
                os.makedirs(data_dir)
            except OSError as e:
                log.error(_("Could not create {directory}: {error}").format(directory=data_dir, error=e), file=sys.stderr)
            else:
                log.info(_("Created {directory}").format(directory=data_dir))

    def do_handle_local_options(self, options):
        if options.contains('version'):
            print(_('GTimeLog version: {}').format(__version__))
            print(_('Python version: {}').format(sys.version.replace('\n', '')))
            print(_('GTK+ version: {}.{}.{}').format(Gtk.MAJOR_VERSION, Gtk.MINOR_VERSION, Gtk.MICRO_VERSION))
            print(_('PyGI version: {}').format(gi.__version__))
            print(_('Data directory: {}').format(Settings().get_data_dir()))
            print(_('Legacy config directory: {}').format(Settings().get_config_dir()))
            self.check_schema()
            gsettings = Gio.Settings.new("org.gtimelog")
            if not gsettings.get_boolean('settings-migrated'):
                print(_('Settings will be migrated to GSettings (org.gtimelog) on first launch'))
            else:
                print(_('Settings already migrated to GSettings (org.gtimelog)'))
            return 0
        return -1  # send the args to the remote instance for processing

    def do_command_line(self, command_line):
        self.do_activate()
        options = command_line.get_options_dict()
        if options.contains('email-prefs'):
            self.on_preferences(page="email")
        elif options.contains('prefs'):
            self.on_preferences()
        return 0

    def do_startup(self):
        mark_time("in app startup")

        self.check_schema()
        self.create_data_directory()

        Gtk.Application.do_startup(self)

        mark_time("basic app startup done")

        css = Gtk.CssProvider()
        css.load_from_path(CSS_FILE)
        screen = Gdk.Screen.get_default()
        Gtk.StyleContext.add_provider_for_screen(
            screen, css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        mark_time("CSS loaded")

        if Gtk.Settings.get_default().get_property('gtk-shell-shows-app-menu'):
            builder = Gtk.Builder.new_from_file(MENUS_UI_FILE)
            self.set_app_menu(builder.get_object('app_menu'))
            mark_time("menus loaded")

        self.actions = self.Actions(self)

        self.set_accels_for_action("win.detail-level::chronological", ["<Alt>1"])
        self.set_accels_for_action("win.detail-level::grouped", ["<Alt>2"])
        self.set_accels_for_action("win.detail-level::summary", ["<Alt>3"])
        self.set_accels_for_action("win.time-range::day", ["<Alt>4"])
        self.set_accels_for_action("win.time-range::week", ["<Alt>5"])
        self.set_accels_for_action("win.time-range::month", ["<Alt>6"])
        self.set_accels_for_action("win.log-order::start-time", ["<Alt>7"])
        self.set_accels_for_action("win.log-order::name", ["<Alt>8"])
        self.set_accels_for_action("win.log-order::duration", ["<Alt>9"])
        self.set_accels_for_action("win.log-order::task-list", ["<Alt>0"])
        self.set_accels_for_action("win.show-task-pane", ["F9"])
        self.set_accels_for_action("win.show-menu", ["F10"])
        self.set_accels_for_action("win.show-search-bar", ["<Primary>F"])
        self.set_accels_for_action("win.go-back", ["<Alt>Left"])
        self.set_accels_for_action("win.go-forward", ["<Alt>Right"])
        self.set_accels_for_action("win.go-home", ["<Alt>Home"])
        self.set_accels_for_action("win.focus-task-entry", ["<Primary>L"])
        self.set_accels_for_action("win.edit-last-entry", ["<Primary><Shift>BackSpace"])
        self.set_accels_for_action("app.edit-log", ["<Primary>E"])
        self.set_accels_for_action("app.edit-tasks", ["<Primary>T"])
        self.set_accels_for_action("app.shortcuts", ["<Primary>question"])
        self.set_accels_for_action("app.preferences", ["<Primary>P"])
        self.set_accels_for_action("app.quit", ["<Primary>Q"])
        self.set_accels_for_action("win.report", ["<Primary>D"])
        self.set_accels_for_action("win.cancel-report", ["Escape"])
        self.set_accels_for_action("win.send-report", ["<Primary>Return"])

        mark_time("app startup done")

    def on_quit(self, action, parameter):
        self.quit()

    def open_in_editor(self, filename):
        self.create_if_missing(filename)
        if os.name == 'nt':
            os.startfile(filename)
        else:
            uri = GLib.filename_to_uri(filename, None)
            Gtk.show_uri(None, uri, Gdk.CURRENT_TIME)

    def on_edit_log(self, action, parameter):
        filename = Settings().get_timelog_file()
        self.open_in_editor(filename)

    def on_edit_tasks(self, action, parameter):
        gsettings = Gio.Settings.new("org.gtimelog")
        if gsettings.get_boolean('remote-task-list'):
            uri = gsettings.get_string('task-list-edit-url')
            if self.get_active_window() is not None:
                self.get_active_window().editing_remote_tasks = True
            Gtk.show_uri(None, uri, Gdk.CURRENT_TIME)
        else:
            filename = Settings().get_task_list_file()
            self.open_in_editor(filename)

    def on_refresh_tasks(self, action, parameter):
        gsettings = Gio.Settings.new("org.gtimelog")
        if gsettings.get_boolean('remote-task-list'):
            if self.get_active_window() is not None:
                self.get_active_window().download_tasks()

    def create_if_missing(self, filename):
        if not os.path.exists(filename):
            open(filename, 'a').close()

    def on_shortcuts(self, action, parameter):
        builder = Gtk.Builder.new_from_file(SHORTCUTS_UI_FILE)
        shortcuts_window = builder.get_object('shortcuts_window')
        shortcuts_window.set_transient_for(self.get_active_window())
        shortcuts_window.show_all()

    def get_contributors(self):
        contributors = []
        with open(CONTRIBUTORS_FILE, encoding='utf-8') as f:
            for line in f:
                if line.startswith('- '):
                    contributors.append(line[2:].strip())
        return sorted(contributors)

    def on_about(self, action, parameter):
        # Note: must create a new dialog (which means a new Gtk.Builder)
        # on every invocation.
        builder = Gtk.Builder.new_from_file(ABOUT_DIALOG_UI_FILE)
        about_dialog = builder.get_object('about_dialog')
        about_dialog.set_version(__version__)
        about_dialog.set_authors(self.get_contributors())
        about_dialog.set_transient_for(self.get_active_window())
        about_dialog.connect("response", lambda *args: about_dialog.destroy())
        about_dialog.show()

    def on_preferences(self, action=None, parameter=None, page=None):
        if self.are_there_any_modals():
            # Don't let a user invoke this recursively via gtimelog --prefs
            return
        preferences = PreferencesDialog(self.get_active_window(), page=page)
        preferences.connect("response", lambda *args: preferences.destroy())
        preferences.run()

    def are_there_any_modals(self):
        # Fix for https://github.com/gtimelog/gtimelog/issues/127
        return any(window.get_modal()
                   for window in Gtk.Window.list_toplevels())

    def do_activate(self):
        mark_time("in app activate")
        window = self.get_active_window()
        if window is not None:
            # window.present() doesn't work on wayland:
            # https://gitlab.gnome.org/GNOME/gtk/issues/624#note_119092
            window.present_with_time(GLib.get_monotonic_time() // 1000)
            # the above workaround stopped working on gnome-shell 44, but maybe
            # window.present() will be fixed one day?
            window.present()
            return

        window = Window(self)
        mark_time("have window")
        self.add_window(window)
        mark_time("added window")
        window.show()
        mark_time("showed window")

        GLib.idle_add(mark_time, "in main loop")

        mark_time("app activate done")


def copy_properties(src, dest):
    blacklist = (
        'events', 'child', 'parent', 'input-hints', 'buffer', 'tabs',
        'completion', 'model', 'type',
        'progress-', 'primary-icon-', 'secondary-icon-',
    )
    RW = GObject.ParamFlags.READWRITE
    for prop in src.props:
        if prop.flags & GObject.ParamFlags.DEPRECATED != 0:
            continue
        if prop.flags & RW != RW:
            continue
        if prop.name.startswith(blacklist):
            continue
        setattr(dest.props, prop.name, getattr(src.props, prop.name))


def swap_widget(builder, name, replacement):
    original = builder.get_object(name)
    copy_properties(original, replacement)
    parent = original.get_parent()
    if isinstance(parent, Gtk.Box):
        expand, fill, padding, pack_type = parent.query_child_packing(original)
        position = parent.get_children().index(original)
    parent.remove(original)
    parent.add(replacement)
    if isinstance(parent, Gtk.Box):
        parent.set_child_packing(replacement, expand, fill, padding, pack_type)
        parent.reorder_child(replacement, position)
    original.destroy()


REPORT_KINDS = {
    # map time_range values to report_kind values
    'day': ReportRecord.DAILY,
    'week': ReportRecord.WEEKLY,
    'month': ReportRecord.MONTHLY,
}


class Window(Gtk.ApplicationWindow):

    timelog = GObject.Property(
        type=object, default=None, nick='Time log',
        blurb='Time log object')

    tasks = GObject.Property(
        type=object, default=None, nick='Tasks',
        blurb='Task list object')

    date = GObject.Property(
        type=object, default=None, nick='Date',
        blurb='Date to show (None tracks today)')

    detail_level = GObject.Property(
        type=str, default='chronological', nick='Detail level',
        blurb='Detail level to show (chronological/grouped/summary)')

    time_range = GObject.Property(
        type=str, default='day', nick='Time range',
        blurb='Time range to show (day/week/month)')

    log_order = GObject.Property(
        type=str, default='start-time', nick='Log Order',
        blurb='Log order for Tasks/Groups (start-time/name/duration/task-list)')

    filter_text = GObject.Property(
        type=str, default='', nick='Filter text',
        blurb='Show only tasks matching this substring')

    class Actions(object):

        simple_actions = [
            'go-back',
            'go-forward',
            'go-home',
            'focus-task-entry',
            'add-entry',
            'edit-last-entry',
            'report',
            'send-report',
            'cancel-report',
        ]

        def __init__(self, win):
            PropertyAction = Gio.PropertyAction

            self.detail_level = PropertyAction.new("detail-level", win, "detail-level")
            win.add_action(self.detail_level)

            self.time_range = PropertyAction.new("time-range", win, "time-range")
            win.add_action(self.time_range)

            self.log_order = PropertyAction.new("log-order", win, "log-order")
            win.add_action(self.log_order)

            self.show_view_menu = PropertyAction.new("show-view-menu", win.view_button, "active")
            win.add_action(self.show_view_menu)

            self.show_task_pane = PropertyAction.new("show-task-pane", win.task_pane, "visible")
            win.add_action(self.show_task_pane)

            self.show_menu = PropertyAction.new("show-menu", win.menu_button, "active")
            win.add_action(self.show_menu)

            self.show_search_bar = PropertyAction.new("show-search-bar", win.search_bar, "search-mode-enabled")
            win.add_action(self.show_search_bar)

            for action_name in self.simple_actions:
                action = Gio.SimpleAction.new(action_name, None)
                action.connect('activate', getattr(win, 'on_' + action_name.replace('-', '_')))
                win.add_action(action)
                setattr(self, action_name.replace('-', '_'), action)

    def __init__(self, app):
        Gtk.ApplicationWindow.__init__(self, application=app, icon_name='gtimelog')

        self._watches = {}
        self._download = None
        self._date = None
        self._showing_today = None
        self._window_size_update_timeout = None
        self.editing_remote_tasks = False
        self.timelog = None
        self.tasks = None
        self.app = app

        mark_time("loading ui")
        builder = Gtk.Builder.new_from_file(UI_FILE)
        mark_time("main ui loaded")
        builder.add_from_file(MENUS_UI_FILE)
        mark_time("menus loaded")

        # I want to use a custom Gtk.ApplicationWindow subclass, but I
        # also want to be able to edit the .ui file with Glade.  So I use
        # a regular ApplicationWindow in the .ui file, then steal its
        # children and add them into my custom window instance.
        main_window = builder.get_object('main_window')
        main_stack = builder.get_object('main_stack')
        headerbar = builder.get_object('headerbar')
        copy_properties(main_window, self)
        main_window.set_titlebar(None)
        main_window.remove(main_stack)
        self.add(main_stack)
        self.set_titlebar(headerbar)

        # Cannot store these in the same .ui file nor hook them up in the
        # .ui because glade doesn't support that and strips both the
        # <menu> and the menu-model property on save.
        self.view_button = builder.get_object("view_button")
        self.menu_button = builder.get_object("menu_button")
        self.menu_button.set_menu_model(builder.get_object('window_menu'))
        self.view_button.set_menu_model(builder.get_object('view_menu'))

        self.main_stack = main_stack
        self.paned = builder.get_object("paned")
        self.task_pane_button = builder.get_object("task_pane_button")
        self.back_button = builder.get_object("back_button")
        self.forward_button = builder.get_object("forward_button")
        self.today_button = builder.get_object("today_button")
        self.send_report_button = builder.get_object("send_report_button")
        self.cancel_report_button = builder.get_object("cancel_report_button")
        self.sender_entry = builder.get_object("sender_entry")
        self.recipient_entry = builder.get_object("recipient_entry")
        self.subject_entry = builder.get_object("subject_entry")
        self.tasks_infobar = builder.get_object("tasks_infobar")
        self.tasks_infobar_label = builder.get_object("tasks_infobar_label")
        self.infobar = builder.get_object("report_infobar")
        self.infobar.connect('response', lambda *args: self.infobar.hide())
        self.infobar_label = builder.get_object("infobar_label")
        self.headerbar = builder.get_object('headerbar')
        self.time_label = builder.get_object('time_label')
        self.task_entry = TaskEntry()
        swap_widget(builder, 'task_entry', self.task_entry)
        self.task_entry.grab_focus() # I specified this in the .ui file but it gets ignored
        self.add_button = builder.get_object('add_button')
        self.add_button.grab_default() # I specified this in the .ui file but it gets ignored
        self.log_view = LogView()
        swap_widget(builder, 'log_view', self.log_view)
        self.bind_property('timelog', self.task_entry, 'timelog', GObject.BindingFlags.DEFAULT)
        self.bind_property('timelog', self.log_view, 'timelog', GObject.BindingFlags.DEFAULT)
        self.bind_property('showing_today', self.log_view, 'showing_today', GObject.BindingFlags.DEFAULT)
        self.bind_property('date', self.log_view, 'date', GObject.BindingFlags.DEFAULT)
        self.bind_property('detail_level', self.log_view, 'detail_level', GObject.BindingFlags.SYNC_CREATE)
        self.bind_property('time_range', self.log_view, 'time_range', GObject.BindingFlags.SYNC_CREATE)
        self.bind_property('log_order', self.log_view, 'log_order', GObject.BindingFlags.SYNC_CREATE)
        self.task_entry.bind_property('text', self.log_view, 'current_task', GObject.BindingFlags.DEFAULT)
        self.bind_property('subtitle', self.headerbar, 'subtitle', GObject.BindingFlags.DEFAULT)
        self.bind_property('filter_text', self.log_view, 'filter_text', GObject.BindingFlags.DEFAULT)
        self.bind_property('tasks', self.log_view, 'tasks', GObject.BindingFlags.DEFAULT)

        self.search_bar = builder.get_object("search_bar")
        self.search_entry = builder.get_object("search_entry")
        self.search_entry.connect('search-changed', self.on_search_changed)

        self.task_pane = builder.get_object("task_pane")
        self.task_list = TaskListView()
        swap_widget(builder, 'task_list', self.task_list)
        self.task_list.connect('row-activated', self.task_list_row_activated)
        self.bind_property('tasks', self.task_list, 'tasks', GObject.BindingFlags.DEFAULT)

        self.actions = self.Actions(self)
        self.actions.add_entry.set_enabled(False)
        self.actions.send_report.set_enabled(False)

        self.report_view = ReportView()
        swap_widget(builder, 'report_view', self.report_view)
        self.bind_property('timelog', self.report_view, 'timelog', GObject.BindingFlags.DEFAULT)
        self.bind_property('date', self.report_view, 'date', GObject.BindingFlags.DEFAULT)
        self.bind_property('time_range', self.report_view, 'time_range', GObject.BindingFlags.SYNC_CREATE)
        self.sender_entry.bind_property('text', self.report_view, 'sender', GObject.BindingFlags.SYNC_CREATE)
        self.recipient_entry.bind_property('text', self.report_view, 'recipient', GObject.BindingFlags.SYNC_CREATE)
        self.report_view.bind_property('subject', self.subject_entry, 'text', GObject.BindingFlags.DEFAULT)
        self.report_view.connect('notify::recipient', self.update_send_report_availability)
        self.report_view.connect('notify::body', self.update_send_report_availability)
        self.report_view.connect('notify::report-status', self.update_already_sent_indication)
        self.update_send_report_availability()

        mark_time('window created')

        self.load_settings()

        self.date = None  # initialize today's date

        self.task_entry.connect('changed', self.task_entry_changed)
        self.connect('notify::detail-level', self.detail_level_changed)
        self.connect('notify::time-range', self.time_range_changed)
        self.connect('focus-in-event', self.gained_focus)
        mark_time('window ready')

        GLib.idle_add(self.load_log)
        GLib.idle_add(self.load_tasks)
        self.tick(True)
        # In theory we could wake up once every 60 seconds.  Shame that
        # there's no timeout_add_minutes.  I don't want to use
        # timeout_add_seconds(60) because that wouldn't be aligned to a
        # minute boundary, so we would delay updating the current time
        # unnecessarily.
        GLib.timeout_add_seconds(1, self.tick)

    def load_settings(self):
        self.gsettings = Gio.Settings.new("org.gtimelog")
        self.gsettings.bind('detail-level', self, 'detail-level', Gio.SettingsBindFlags.DEFAULT)
        self.gsettings.bind('log-order', self, 'log-order', Gio.SettingsBindFlags.DEFAULT)
        self.gsettings.bind('show-task-pane', self.task_pane, 'visible', Gio.SettingsBindFlags.DEFAULT)
        self.gsettings.bind('hours', self.log_view, 'hours', Gio.SettingsBindFlags.DEFAULT)
        self.gsettings.bind('office-hours', self.log_view, 'office-hours', Gio.SettingsBindFlags.DEFAULT)
        self.gsettings.bind('name', self.report_view, 'name', Gio.SettingsBindFlags.DEFAULT)
        self.gsettings.bind('sender', self.sender_entry, 'text', Gio.SettingsBindFlags.DEFAULT)
        self.gsettings.bind('list-email', self.recipient_entry, 'text', Gio.SettingsBindFlags.DEFAULT)
        self.gsettings.bind('report-style', self.report_view, 'report-style', Gio.SettingsBindFlags.DEFAULT)
        self.gsettings.bind('remote-task-list', self.app.actions.refresh_tasks, 'enabled', Gio.SettingsBindFlags.DEFAULT)
        self.gsettings.bind('gtk-completion', self.task_entry, 'gtk-completion-enabled', Gio.SettingsBindFlags.DEFAULT)
        self.gsettings.connect('changed::remote-task-list', self.load_tasks)
        self.gsettings.connect('changed::task-list-url', self.load_tasks)
        self.gsettings.connect('changed::task-list-edit-url', self.update_edit_tasks_availability)
        self.gsettings.connect('changed::virtual-midnight', self.virtual_midnight_changed)
        self.update_edit_tasks_availability()

        x, y = self.gsettings.get_value('window-position')
        w, h = self.gsettings.get_value('window-size')
        tpp = self.gsettings.get_int('task-pane-position')
        self.resize(w, h)
        if (x, y) != (-1, -1):
            self.move(x, y)
        self.paned.set_position(tpp)
        self.paned.connect('notify::position', self.delay_store_window_size)
        self.connect("configure-event", self.delay_store_window_size)

        if not self.gsettings.get_boolean('settings-migrated'):
            old_settings = Settings()
            loaded_files = old_settings.load()
            if old_settings.summary_view:
                self.gsettings.set_string('detail-level', 'summary')
            elif old_settings.chronological:
                self.gsettings.set_string('detail-level', 'chronological')
            else:
                self.gsettings.set_string('detail-level', 'grouped')
            self.gsettings.set_boolean('show-task-pane', old_settings.show_tasks)
            self.gsettings.set_double('hours', old_settings.hours)
            self.gsettings.set_double('office-hours', old_settings.office_hours)
            self.gsettings.set_string('name', old_settings.name)
            self.gsettings.set_string('sender', old_settings.sender)
            self.gsettings.set_string('list-email', old_settings.email)
            self.gsettings.set_string('report-style', old_settings.report_style)
            self.gsettings.set_string('task-list-url', old_settings.task_list_url)
            self.gsettings.set_boolean('remote-task-list', bool(old_settings.task_list_url))
            for arg in old_settings.edit_task_list_cmd.split():
                if arg.startswith(('http://', 'https://')):
                    self.gsettings.set_string('task-list-edit-url', arg)
            vm = old_settings.virtual_midnight
            self.gsettings.set_value('virtual-midnight', GLib.Variant('(ii)', (vm.hour, vm.minute)))
            self.gsettings.set_boolean('gtk-completion', bool(old_settings.enable_gtk_completion))
            self.gsettings.set_boolean('settings-migrated', True)
            if loaded_files:
                log.info(_('Settings from {filename} migrated to GSettings (org.gtimelog)').format(filename=old_settings.get_config_file()))

        mark_time('settings loaded')

    def load_log(self):
        mark_time("loading timelog")
        timelog = TimeLog(Settings().get_timelog_file(), self.get_virtual_midnight())
        mark_time("timelog loaded")
        self.timelog = timelog
        self.tick(True)
        self.enable_add_entry()
        mark_time("timelog presented")
        self.watch_file(self.timelog.filename, self.on_timelog_file_changed)

    def load_tasks(self, *args):
        mark_time("loading tasks")
        if self.gsettings.get_boolean('remote-task-list'):
            filename = Settings().get_task_list_cache_file()
            tasks = TaskList(filename)
            self.download_tasks()
        else:
            filename = Settings().get_task_list_file()
            tasks = TaskList(filename)
            self.tasks_infobar.hide()
        mark_time("tasks loaded")
        if self.tasks:
            self.unwatch_file(self.tasks.filename)
        self.tasks = tasks
        mark_time("tasks presented")
        self.watch_file(self.tasks.filename, self.on_tasks_file_changed)
        self.update_edit_tasks_availability()

    def update_edit_tasks_availability(self, *args):
        if self.gsettings.get_boolean('remote-task-list'):
            can_edit_tasks = bool(self.gsettings.get_string('task-list-edit-url'))
        else:
            can_edit_tasks = True
        self.app.actions.edit_tasks.set_enabled(can_edit_tasks)

    def update_send_report_availability(self, *args):
        if self.main_stack.get_visible_child_name() == 'report':
            can_send = bool(self.report_view.recipient and self.report_view.body)
        else:
            can_send = False
        self.actions.send_report.set_enabled(can_send)

    def update_already_sent_indication(self, *args):
        if self.report_view.report_status == 'sent':
            self.infobar_label.set_text(_("Report already sent"))
            self.infobar.show()
            # https://github.com/gtimelog/gtimelog/issues/89
            self.infobar.queue_resize()
        elif self.report_view.report_status == 'sent-elsewhere':
            self.infobar_label.set_text(
                _("Report already sent (to {})").format(
                    self.report_view.report_sent_to))
            self.infobar.show()
            # https://github.com/gtimelog/gtimelog/issues/89
            self.infobar.queue_resize()
        else:
            self.infobar.hide()

    def cancel_tasks_download(self, hide=True):
        if self._download:
            self.cancellable.cancel()
            self._download = None
        if hide:
            self.tasks_infobar.hide()

    def download_tasks(self):
        # hide=False and queue_resize() are needed to work around
        # this bug: https://github.com/gtimelog/gtimelog/issues/89
        self.cancel_tasks_download(hide=False)

        url = self.gsettings.get_string('task-list-url')
        if not url:
            log.debug("Not downloading tasks: URL not specified")
            return
        cache_filename = Settings().get_task_list_cache_file()
        self.tasks_infobar.set_message_type(Gtk.MessageType.INFO)
        self.tasks_infobar_label.set_text(_("Downloading tasks..."))
        self.cancellable = Gio.Cancellable()
        self.tasks_infobar.connect('response', lambda *args: self.cancel_tasks_download())
        self.tasks_infobar.show()
        self.tasks_infobar.queue_resize()
        log.debug("Downloading tasks from %s", url)
        message = Soup.Message.new('GET', url)
        self._download = (message, url)
        message.connect('authenticate', authenticator.http_auth_cb)
        soup_session.send_and_read_async(
            message,
            GLib.PRIORITY_DEFAULT,
            self.cancellable,
            self.tasks_downloaded,
            cache_filename
        )

    def tasks_downloaded(self, session, result, cache_filename):
        message = soup_session.get_async_result_message(result)
        status_code = message.get_status()
        if status_code != Soup.Status.OK:
            url = message.get_uri().to_string()

            log.error("Failed to download tasks from %s: %d %s",
                      url, status_code, message.get_reason_phrase())
            self.tasks_infobar.set_message_type(Gtk.MessageType.ERROR)
            self.tasks_infobar_label.set_text(_("Download failed."))
            self.tasks_infobar.connect('response', lambda *args: self.tasks_infobar.hide())
            self.tasks_infobar.show()
        else:
            content = soup_session.send_and_read_finish(result).get_data().decode()
            log.debug("Successfully downloaded tasks:\n  %s",
                      content.replace('\n', '\n  '))
            with open(cache_filename, 'w') as f:
                f.write(content)
            self.check_reload_tasks()
            self.tasks_infobar.hide()
        self._download = None

    def gained_focus(self, *args):
        if self.editing_remote_tasks:
            self.download_tasks()
            self.editing_remote_tasks = False
        # In case inotify magic fails, let's allow the user to refresh by
        # switching focus.
        self.check_reload()
        self.check_reload_tasks()

    def virtual_midnight_changed(self, *args):
        if self.timelog:
            # This is only partially correct: we're not reloading old logs.
            # (Reloading old logs would also be partially incorrect.)
            self.timelog.virtual_midnight = self.get_virtual_midnight()

    def delay_store_window_size(self, *args):
        # Delaying the save to avoid performance problems that gnome-music had
        # (see https://bugzilla.gnome.org/show_bug.cgi?id=745651)
        if self._window_size_update_timeout is None:
            self._window_size_update_timeout = GLib.timeout_add(500, self.store_window_size)

    def _store_window_size(self):
        position = self.get_position()
        size = self.get_size()
        tpp = self.paned.get_position()
        old_position = self.gsettings.get_value('window-position')
        old_size = self.gsettings.get_value('window-size')
        old_tpp = self.gsettings.get_int('task-pane-position')
        if tuple(size) != tuple(old_size):
            self.gsettings.set_value('window-size', GLib.Variant('(ii)', size))
        if tuple(position) != tuple(old_position):
            self.gsettings.set_value('window-position', GLib.Variant('(ii)', position))
        if tpp != old_tpp:
            self.gsettings.set_int('task-pane-position', tpp)

    def store_window_size(self):
        if self.props.window is not None and not self.is_maximized_in_any_way():
            self._store_window_size()
        GLib.source_remove(self._window_size_update_timeout)
        self._window_size_update_timeout = None
        return False

    def is_maximized_in_any_way(self):
        # NB: This fails to catch horizontally maximized windows because
        # GDK ignores the _NET_WM_STATE_MAXIMIZED_HORZ atom when it's not
        # accompanied by _NET_WM_STATE_MAXIMIZED_VERT.  We only catch
        # vertically maximized windows because GDK thinks they're tiled.
        assert self.props.window is not None
        MAXIMIZED_IN_ANY_WAY = (Gdk.WindowState.MAXIMIZED
                                | Gdk.WindowState.TILED
                                | Gdk.WindowState.FULLSCREEN)
        return (self.props.window.get_state() & MAXIMIZED_IN_ANY_WAY) != 0

    def watch_file(self, filename, callback):
        log.debug('adding watch on %s', filename)
        gf = Gio.File.new_for_path(filename)
        gfm = gf.monitor_file(Gio.FileMonitorFlags.NONE, None)
        gfm.connect('changed', callback)
        self._watches[filename] = (gfm, None)  # keep a reference so it doesn't get garbage collected
        if os.path.islink(filename):
            realpath = os.path.join(os.path.dirname(filename), os.readlink(filename))
            log.debug('%s is a symlink, adding a watch on %s', filename, realpath)
            self._watches[filename] = (gfm, realpath)
            if realpath not in self._watches:  # protect against infinite loops
                self.watch_file(realpath, callback)

    def unwatch_file(self, filename):
        # watch_file(a_symlink, callback) creates multiple watches, so be sure to unwatch them all
        while filename in self._watches:
            log.debug('removing watch on %s', filename)
            filename = self._watches.pop(filename)[1]

    def get_last_time(self):
        if self.timelog is None:
            return None
        return self.timelog.window.last_time()

    def get_time_window(self):
        if self.time_range == 'day':
            return self.timelog.window_for_day(self.date)
        elif self.time_range == 'week':
            return self.timelog.window_for_week(self.date)
        elif self.time_range == 'month':
            return self.timelog.window_for_month(self.date)

    def get_now(self):
        return datetime.datetime.now().replace(second=0, microsecond=0)

    def get_virtual_midnight(self):
        h, m = self.gsettings.get_value('virtual-midnight')
        return datetime.time(h, m)

    def get_today(self):
        return virtual_day(datetime.datetime.now(), self.get_virtual_midnight())

    def get_current_task(self):
        """Return the current task entry text (as Unicode)."""
        entry = self.task_entry.get_text()
        if isinstance(entry, bytes):
            entry = entry.decode('UTF-8')
        return entry.strip()

    @date.getter
    def date(self):
        return self._date

    @date.setter
    def date(self, new_date):
        # Enforce strict typing
        if new_date is not None and not isinstance(new_date, datetime.date):
            new_date = None

        # Going back to today is the same as going home
        today = self.get_today()
        if new_date is None or new_date >= today:
            new_date = today

        old_date = self._date
        old_showing_today = self._showing_today
        self._date = new_date

        if new_date == today:
            self._showing_today = True
            self.actions.go_home.set_enabled(False)
            self.actions.go_forward.set_enabled(False)
        else:
            self._showing_today = False
            self.actions.go_home.set_enabled(True)
            self.actions.go_forward.set_enabled(True)

        if old_showing_today != self._showing_today:
            self.notify('showing_today')
        if old_date != self._date:
            self.notify('subtitle')

    @GObject.Property(
        type=bool, default=True, nick='Showing today',
        blurb='Currently visible time range includes today')
    def showing_today(self):
        return self._showing_today

    @GObject.Property(
        type=str, nick='Subtitle',
        blurb='Description of the visible time range')
    def subtitle(self):
        date = self.date
        if not date:
            return ''
        if self.time_range == 'day':
            return _("{0:%A, %Y-%m-%d} (week {1:0>2})").format(
                date, date.isocalendar()[1])
        elif self.time_range == 'week':
            monday = date - datetime.timedelta(date.weekday())
            sunday = monday + datetime.timedelta(6)
            isoyear, isoweek = date.isocalendar()[:2]
            return _("{0}, week {1} ({2:%B %-d}-{3:%-d})").format(
                isoyear, isoweek, monday, sunday)
        elif self.time_range == 'month':
            return _("{0:%B %Y}").format(date)

    def detail_level_changed(self, obj, param_spec):
        assert self.detail_level in {'chronological', 'grouped', 'summary'}
        self.notify('subtitle')

    def time_range_changed(self, obj, param_spec):
        assert self.time_range in {'day', 'week', 'month'}
        self.notify('subtitle')

    def on_search_changed(self, *args):
        self.filter_text = self.search_entry.get_text()

    def on_go_back(self, action, parameter):
        if self.time_range == 'day':
            self.date -= datetime.timedelta(1)
        elif self.time_range == 'week':
            self.date -= datetime.timedelta(7)
        elif self.time_range == 'month':
            self.date = prev_month(self.date)

    def on_go_forward(self, action, parameter):
        if self.time_range == 'day':
            self.date += datetime.timedelta(1)
        elif self.time_range == 'week':
            self.date += datetime.timedelta(7)
        elif self.time_range == 'month':
            self.date = next_month(self.date)

    def on_go_home(self, action, parameter):
        self.date = None

    def on_focus_task_entry(self, action, parameter):
        self.task_entry.grab_focus()

    def on_edit_last_entry(self, action, parameter):
        text = self.timelog.remove_last_entry()
        if text is not None:
            self.date = None
            self.notify('timelog')
            self.tick(True)
            self.task_entry.set_text(text)
        self.task_entry.grab_focus()
        self.task_entry.select_region(-1, -1)

    def on_add_entry(self, action, parameter):
        mark_time()
        mark_time("on_add_entry")
        entry = self.get_current_task()
        entry, now = self.timelog.parse_correction(entry)
        if not entry:
            return
        mark_time("adding the entry")
        if not self.showing_today:
            self.date = None  # jump to today
            mark_time("jumped to today")

        previous_day = self.timelog.day
        self.timelog.append(entry, now)
        mark_time("appended")
        same_day = self.timelog.day == previous_day
        self.log_view.entry_added(same_day)
        mark_time("log_view updated")
        self.task_entry.entry_added()
        self.task_entry.set_text('')
        self.task_entry.grab_focus()
        mark_time("focus grabbed")
        self.tick(True)
        mark_time("label updated")

    def on_report(self, action, parameter):
        if self.main_stack.get_visible_child_name() == 'report':
            self.on_cancel_report()
        else:
            self.saved_date = self.date
            self.saved_time_range = self.time_range
            self.main_stack.set_visible_child_name('report')
            self.view_button.hide()
            self.task_pane_button.hide()
            self.menu_button.hide()
            self.cancel_report_button.show()
            self.send_report_button.show()
            self.report_view.show()
            self.headerbar.set_show_close_button(False)
            self.set_title(_("Report"))
            self.update_send_report_availability()

    def on_send_report(self, action, parameter):
        if self.main_stack.get_visible_child_name() != 'report':
            log.debug("Not sending report: not in report mode")
            return
        sender = self.report_view.sender
        recipient = self.report_view.recipient
        subject = self.report_view.subject
        body = self.report_view.body
        if not body:
            log.debug("Not sending report: no body")
            return
        if not recipient:
            log.debug("Not sending report: no destination")
            return
        try:
            self.send_email(sender, recipient, subject, body)
        except EmailError as e:
            self.infobar_label.set_text(
                _("Couldn't send email to {}: {}.").format(recipient, e))
            self.infobar.show()
        else:
            self.record_sent_email(self.report_view.time_range,
                                   self.report_view.date,
                                   recipient)
            self.on_cancel_report()

    def send_email(self, sender, recipient, subject, body):
        smtp_server = self.gsettings.get_string('smtp-server')
        smtp_username = self.gsettings.get_string('smtp-username')
        callback = functools.partial(self._send_email, sender, recipient, subject, body)
        if smtp_username:
            start_smtp_password_lookup(smtp_server, smtp_username, callback)
        else:
            callback('')

    def _send_email(self, sender, recipient, subject, body, smtp_password):
        smtp_server = self.gsettings.get_string('smtp-server')
        smtp_port = self.gsettings.get_int('smtp-port')
        smtp_username = self.gsettings.get_string('smtp-username')

        sender_name, sender_address = parseaddr(sender)
        recipient_name, recipient_address = parseaddr(recipient)
        msg = prepare_message(sender, recipient, subject, body)

        mail_protocol = self.gsettings.get_string('mail-protocol')
        factory, starttls = MAIL_PROTOCOLS[mail_protocol]
        try:
            log.debug('Connecting to %s port %s',
                      smtp_server, smtp_port or '(default)')
            with closing(factory(smtp_server, smtp_port)) as smtp:
                if DEBUG:
                    smtp.set_debuglevel(1)
                if starttls:
                    log.debug('Issuing STARTTLS')
                    smtp.starttls()
                if smtp_username:
                    log.debug('Logging in as %s', smtp_username)
                    smtp.login(smtp_username, smtp_password)
                log.debug('Sending email from %s to %s',
                          sender_address, recipient_address)
                smtp.sendmail(sender_address, [recipient_address], msg.as_string())
                log.debug('Closing SMTP connection')
        except (OSError, smtplib.SMTPException) as e:
            log.error(_("Couldn't send mail: %s"), e)
            raise EmailError(e)
        else:
            log.debug('Email sent!')

    def record_sent_email(self, time_range, date, recipient):
        record = self.report_view.record
        try:
            report_kind = REPORT_KINDS[time_range]
            record.record(report_kind, date, recipient)
        except IOError as e:
            log.error(_("Couldn't append to {}: {}").format(record.filename, e))

    def on_cancel_report(self, action=None, parameter=None):
        if self.main_stack.get_visible_child_name() != 'report':
            self.search_bar.set_search_mode(False)
            self.filter_text = ''
            return
        self.main_stack.set_visible_child_name('entry')
        self.view_button.show()
        self.task_pane_button.show()
        self.menu_button.show()
        self.cancel_report_button.hide()
        self.send_report_button.hide()
        self.report_view.hide()
        self.infobar.hide()
        self.headerbar.set_show_close_button(True)
        self.set_title(_("Time Log"))
        self.date = self.saved_date
        self.time_range = self.saved_time_range
        self.update_send_report_availability()
        self.add_button.grab_default() # huh

    def on_timelog_file_changed(self, monitor, file, other_file, event_type):
        # When I edit timelog.txt with vim, I get a series of notifications:
        # - Gio.FileMonitorEvent.DELETED
        # - Gio.FileMonitorEvent.CREATED
        # - Gio.FileMonitorEvent.CHANGED
        # - Gio.FileMonitorEvent.CHANGED
        # - Gio.FileMonitorEvent.CHANGES_DONE_HINT
        # - Gio.FileMonitorEvent.ATTRIBUTE_CHANGED
        # So, plan: react to CHANGES_DONE_HINT at once, but in case some
        # systems/OSes don't ever send it, react to other events after a
        # short delay, so we wouldn't have to reload the file more than
        # once.
        log.debug('watch on %s reports %s', file.get_path(), event_type.value_nick.upper())
        if event_type == Gio.FileMonitorEvent.CHANGES_DONE_HINT:
            self.check_reload()
        else:
            GLib.timeout_add_seconds(1, self.check_reload)

    def on_tasks_file_changed(self, monitor, file, other_file, event_type):
        log.debug('watch on %s reports %s', file.get_path(), event_type.value_nick.upper())
        if event_type == Gio.FileMonitorEvent.CHANGES_DONE_HINT:
            self.check_reload_tasks()
        else:
            GLib.timeout_add_seconds(1, self.check_reload_tasks)

    def check_reload(self):
        if self.timelog and self.timelog.check_reload():
            self.notify('timelog')
            self.tick(True)

    def check_reload_tasks(self):
        if self.tasks and self.tasks.check_reload():
            self.notify('tasks')

    def enable_add_entry(self):
        enabled = self.timelog is not None and self.get_current_task()
        self.actions.add_entry.set_enabled(enabled)

    def task_entry_changed(self, widget):
        self.enable_add_entry()

    def task_list_row_activated(self, treeview, path, view_column):
        task = self.task_list.get_task_for_row(path)
        self.task_entry.set_text(task)
        # There's a race here: sometimes the GDK_2BUTTON_PRESS signal is
        # handled _after_ row-activated, which makes the tree control steal
        # the focus back from the task entry.  To avoid this, wait until all
        # the events have been handled.
        GLib.idle_add(self._focus_task_entry)

    def _focus_task_entry(self):
        self.task_entry.grab_focus()
        self.task_entry.set_position(-1)

    def tick(self, force_update=False):
        now = self.get_now()
        if not force_update and now == self.last_tick:
            # Do not eat CPU unnecessarily: update the time ticker only when
            # the minute changes.
            return True
        self.last_tick = now
        last_time = self.get_last_time()
        if last_time is None:
            self.time_label.set_text(now.strftime(_('%H:%M')))
        else:
            self.time_label.set_text(format_duration(now - last_time))
        self.log_view.now = now
        if self.showing_today and virtual_day(now, self.get_virtual_midnight()) != self.date:
            self.date = None
        return True


class TaskEntry(Gtk.Entry):

    timelog = GObject.Property(
        type=object, default=None, nick='Time log',
        blurb='Time log object')

    completion_limit = GObject.Property(
        type=int, default=1000, nick='Completion limit',
        blurb='Maximum number of items in the completion popup')

    gtk_completion_enabled = GObject.Property(
        type=bool, default=True, nick='Completion enabled',
        blurb='GTK+ completion enabled?')

    def __init__(self):
        Gtk.Entry.__init__(self)
        self.set_up_history()
        self.set_up_completion()
        self.connect('notify::timelog', self.timelog_changed)
        self.connect('notify::completion-limit', self.timelog_changed)
        self.connect('changed', self.on_changed)
        self.connect('notify::gtk-completion-enabled', self.gtk_completion_enabled_changed)

    def set_up_history(self):
        self.history = []
        self.filtered_history = []
        self.history_pos = 0
        self.history_undo = ''

    def set_up_completion(self):
        completion = self.gtk_completion = Gtk.EntryCompletion()
        self.completion_choices = Gtk.ListStore(str)
        self.completion_choices_as_set = set()
        completion.set_model(self.completion_choices)
        completion.set_text_column(0)
        completion.set_match_func(
            self.completion_match_func, self.completion_choices)
        if self.gtk_completion_enabled:
            self.set_completion(completion)

    def completion_match_func(self, completion, search_text, tree_iter, data):
        entry = data.get_value(tree_iter, 0).lower()
        pos = 0
        for char in search_text:
            new_pos = entry.find(char, pos)
            if new_pos == -1:
                return False
            else:
                pos = new_pos
        return True

    def gtk_completion_enabled_changed(self, *args):
        if self.gtk_completion_enabled:
            self.set_completion(self.gtk_completion)
        else:
            self.set_completion(None)

    def timelog_changed(self, *args):
        mark_time('about to initialize history completion')
        self.completion_choices_as_set.clear()
        self.completion_choices.clear()
        if self.timelog is None:
            mark_time('no history')
            return
        self.history = [item[1] for item in self.timelog.items]
        mark_time('history prepared')
        # if there are duplicate entries, we want to keep the last one
        # e.g. if timelog.items contains [a, b, a, c], we want
        # self.completion_choices to be [b, a, c].
        entries = []
        for entry in reversed(self.history):
            if entry not in self.completion_choices_as_set:
                entries.append(entry)
                self.completion_choices_as_set.add(entry)
        mark_time('unique items selected')
        for entry in reversed(entries[:self.completion_limit]):
            self.completion_choices.append([entry])
        mark_time('history completion initialized')

    def entry_added(self):
        if self.timelog is None:
            return
        entry = self.timelog.last_entry().entry
        self.history.append(entry)
        self.history_pos = 0
        if entry not in self.completion_choices_as_set:
            self.completion_choices.append([entry])
            self.completion_choices_as_set.add(entry)

    def on_changed(self, widget):
        self.history_pos = 0

    def do_key_press_event(self, event):
        if event.keyval == Gdk.keyval_from_name('Prior'):
            self._do_history(1)
            return True
        if event.keyval == Gdk.keyval_from_name('Next'):
            self._do_history(-1)
            return True
        return Gtk.Entry.do_key_press_event(self, event)

    def _do_history(self, delta):
        """Handle movement in history."""
        if not self.history:
            return
        if self.history_pos == 0:
            self.history_undo = self.get_text()
            self.filtered_history = uniq([
                entry for entry in self.history
                if entry.startswith(self.history_undo)
            ])
        history = self.filtered_history
        new_pos = max(0, min(self.history_pos + delta, len(history)))
        if new_pos == 0:
            self.set_text(self.history_undo)
            self.set_position(-1)
        else:
            self.set_text(history[-new_pos])
            self.select_region(len(self.history_undo), -1)
        # Do this after on_changed reset history_pos to 0
        self.history_pos = new_pos


class LogView(Gtk.TextView):

    timelog = GObject.Property(
        type=object, default=None, nick='Time log',
        blurb='Time log object')

    date = GObject.Property(
        type=object, default=None, nick='Date',
        blurb='Date to show (None tracks today)')

    showing_today = GObject.Property(
        type=bool, default=True, nick='Showing today',
        blurb='Currently visible time range includes today')

    detail_level = GObject.Property(
        type=str, default='chronological', nick='Detail level',
        blurb='Detail level to show (chronological/grouped/summary)')

    time_range = GObject.Property(
        type=str, default='day', nick='Time range',
        blurb='Time range to show (day/week/month)')

    log_order = GObject.Property(
        type=str, default='start-time', nick='Log order',
        blurb='Log order of tasks/groups (start-time/name/duration/task-list)')

    hours = GObject.Property(
        type=float, default=0, nick='Hours',
        blurb='Target number of work hours per day')

    office_hours = GObject.Property(
        type=float, default=0, nick='Office Hours',
        blurb='Target number of office hours per day')

    current_task = GObject.Property(
        type=str, nick='Current task',
        blurb='Current task in progress')

    now = GObject.Property(
        type=object, default=None, nick='Now',
        blurb='Current date and time')

    filter_text = GObject.Property(
        type=str, default='', nick='Filter text',
        blurb='Show only tasks matching this substring')

    tasks = GObject.Property(
        type=object, nick='Tasks',
        blurb='The task list (an instance of TaskList)')

    def __init__(self):
        Gtk.TextView.__init__(self)
        self._extended_footer = False
        self._footer_mark = None
        self._update_pending = False
        self._footer_update_pending = False
        self.set_up_tabs()
        self.set_up_tags()
        self.connect('notify::timelog', self.queue_update)
        self.connect('notify::date', self.queue_update)
        self.connect('notify::showing-today', self.queue_update)
        self.connect('notify::detail-level', self.queue_update)
        self.connect('notify::time-range', self.queue_update)
        self.connect('notify::log-order', self.queue_update)
        self.connect('notify::hours', self.queue_footer_update)
        self.connect('notify::office-hours', self.queue_footer_update)
        self.connect('notify::current-task', self.queue_footer_update)
        self.connect('notify::now', self.queue_footer_update)
        self.connect('notify::filter-text', self.queue_update)
        self.connect('notify::tasks', self.queue_update)

    def queue_update(self, *args):
        if not self._update_pending:
            self._update_pending = True
            GLib.idle_add(self.populate_log)

    def queue_footer_update(self, *args):
        if not self._footer_update_pending:
            self._footer_update_pending = True
            GLib.idle_add(self.update_footer)

    def set_up_tabs(self):
        pango_context = self.get_pango_context()
        em = pango_context.get_font_description().get_size()
        tabs = Pango.TabArray.new(2, False)
        tabs.set_tab(0, Pango.TabAlign.LEFT, 9 * em)
        tabs.set_tab(1, Pango.TabAlign.LEFT, 12.5 * em)
        self.set_tabs(tabs)

    def set_up_tags(self):
        buffer = self.get_buffer()
        buffer.create_tag('today', foreground='#204a87')     # Tango dark blue
        buffer.create_tag('duration', foreground='#ce5c00')  # Tango dark orange
        buffer.create_tag('time', foreground='#4e9a06')      # Tango dark green
        buffer.create_tag('highlight', foreground='#4e9a06') # Tango dark green
        buffer.create_tag('slacking', foreground='gray')

    def get_time_window(self):
        assert self.timelog is not None
        if self.time_range == 'day':
            return self.timelog.window_for_day(self.date)
        elif self.time_range == 'week':
            return self.timelog.window_for_week(self.date)
        elif self.time_range == 'month':
            return self.timelog.window_for_month(self.date)

    def get_last_time(self):
        assert self.timelog is not None
        return self.timelog.window.last_time()

    def get_current_task_time(self):
        last_time = self.get_last_time()
        if last_time is None:
            return datetime.timedelta(0)
        else:
            return self.now - last_time

    def get_current_task_work_time(self):
        if '**' in self.current_task:
            return datetime.timedelta(0)
        else:
            return self.get_current_task_time()

    def time_left_at_work(self, total_work):
        total_time = total_work + self.get_current_task_work_time()
        return datetime.timedelta(hours=self.hours) - total_time

    def populate_log(self):
        self._update_pending = False
        self.get_buffer().set_text('')
        if self.timelog is None:
            return # not loaded yet
        window = self.get_time_window()
        total = datetime.timedelta(0)
        if self.detail_level == 'chronological':
            prev = None
            for item in window.all_entries():
                first_of_day = prev is None or different_days(prev, item.start, self.timelog.virtual_midnight)
                if first_of_day and prev is not None:
                    self.w("\n")
                if self.time_range != 'day' and first_of_day:
                    self.w(_("{0:%A, %Y-%m-%d}\n").format(item.start))
                if self.filter_text in item.entry:
                    self.write_item(item)
                    total += item.duration
                prev = item.start
        elif self.detail_level == 'grouped':
            work, slack = window.grouped_entries(sorted_by=self.log_order,
                                                 sorted_tasks=self.tasks)
            for start, entry, duration in work + slack:
                if self.filter_text in entry:
                    self.write_group(entry, duration)
                    total += duration
        elif self.detail_level == 'summary':
            entries, totals = window.categorized_work_entries()
            no_cat = totals.pop(None, None)
            categories = sorted(totals.items())
            if no_cat is not None:
                categories = [('no category', no_cat)] + categories
            for category, duration in categories:
                if self.filter_text in category:
                    self.write_group(category, duration)
                    total += duration
        else:
            return # bug!
        if self.filter_text:
            self.w('\n')
            args = [
                (self.filter_text, 'highlight'),
                (format_duration(total), 'duration'),
            ]
            if self.time_range != 'day':
                work_days = window.count_days() or 1
                per_diem = total / work_days
                args.append((format_duration(per_diem), 'duration'))
                self.wfmt(_('Total for {0}: {1} ({2} per day)'), *args)
            else:
                weekly_window = self.timelog.window_for_week(self.date)
                work_days_in_week = weekly_window.count_days() or 1
                week_work, week_slacking = weekly_window.totals(
                    filter_text=self.filter_text)
                week_total = week_work + week_slacking
                args.append((format_duration(week_total), 'duration'))
                per_diem = week_total / work_days_in_week
                args.append((format_duration(per_diem), 'duration'))
                self.wfmt(_('Total for {0}: {1} ({2} this week, {3} per day)'), *args)
            self.w('\n')
        self.reposition_cursor()
        self.add_footer()
        self.scroll_to_end()

    def entry_added(self, same_day):
        if (self.detail_level == 'chronological' and same_day
                and not self.filter_text):
            self.delete_footer()
            self.write_item(self.timelog.last_entry())
            self.add_footer()
            self.scroll_to_end()
        else:
            self.populate_log()

    def reposition_cursor(self):
        where = self.get_buffer().get_end_iter()
        where.backward_cursor_position()
        self.get_buffer().place_cursor(where)

    def scroll_to_end(self):
        # If I do the scrolling immediately, it won't scroll to the end, usually.
        # If I delay the scrolling, it works every time.
        # I only wish I knew how to disable the scroll animation.
        GLib.idle_add(self._scroll_to_end)

    def _scroll_to_end(self):
        buffer = self.get_buffer()
        self.scroll_to_iter(buffer.get_end_iter(), 0, False, 0, 0)

    def write_item(self, item):
        self.w(format_duration(item.duration), 'duration')
        self.w('\t')
        period = _('({0:%H:%M}-{1:%H:%M})').format(item.start, item.stop)
        self.w(period, 'time')
        self.w('\t')
        tag = ('slacking' if '**' in item.entry else None)
        self.w(item.entry + '\n', tag)

    def write_group(self, entry, duration):
        self.w(format_duration(duration), 'duration')
        tag = ('slacking' if '**' in entry else None)
        self.w('\t' + entry + '\n', tag)

    def w(self, text, tag=None):
        """Write some text at the end of the log buffer."""
        buffer = self.get_buffer()
        if tag:
            buffer.insert_with_tags_by_name(buffer.get_end_iter(), text, tag)
        else:
            buffer.insert(buffer.get_end_iter(), text)

    def wfmt(self, fmt, *args):
        """Write formatted text at the end of the log buffer.

        Accepts the same kind of format string as Python's str.format(),
        e.g. "Hello, {0}".

        Each argument should be a tuple (value, tag_name).
        """
        for bit in re.split(r'({\d+(?::[^}]*)?})', fmt):
            if bit.startswith('{'):
                spec = bit[1:-1]
                idx, colon, fmt = spec.partition(':')
                value, tag = args[int(idx)]
                if fmt:
                    value = format(value, fmt)
                self.w(value, tag)
            else:
                self.w(bit)

    def should_have_extended_footer(self):
        return self.showing_today and self.time_range == 'day'

    def update_footer(self):
        self._footer_update_pending = False
        if self._footer_mark is None:
            return
        if self._extended_footer or self.should_have_extended_footer():
            # Update "time left to work"/"at office today"
            self.delete_footer()
            self.add_footer()

    def delete_footer(self):
        buffer = self.get_buffer()
        buffer.delete(
            buffer.get_iter_at_mark(self._footer_mark), buffer.get_end_iter())
        buffer.delete_mark(self._footer_mark)
        self._footer_mark = None

    def add_footer(self):
        buffer = self.get_buffer()
        self._footer_mark = buffer.create_mark(
            'footer', buffer.get_end_iter(), True)
        window = self.get_time_window()
        total_work, total_slacking = window.totals()

        self.w('\n')
        if self.time_range == 'day':
            fmt1 = _('Total work done: {0} ({1} this week, {2} per day)')
            fmt2 = _('Total work done: {0} ({1} this week)')
        elif self.time_range == 'week':
            fmt1 = _('Total work done this week: {0} ({1} per day)')
            fmt2 = _('Total work done this week: {0}')
        elif self.time_range == 'month':
            fmt1 = _('Total work done this month: {0} ({1} per day)')
            fmt2 = _('Total work done this month: {0}')
        args = [(format_duration(total_work), 'duration')]
        if self.time_range == 'day':
            weekly_window = self.timelog.window_for_week(self.date)
            week_total_work, week_total_slacking = weekly_window.totals()
            work_days = weekly_window.count_days()
            args.append((format_duration(week_total_work), 'duration'))
            per_diem = week_total_work / max(1, work_days)
        else:
            work_days = window.count_days()
            per_diem = total_work / max(1, work_days)
        if work_days:
            args.append((format_duration(per_diem), 'duration'))
            self.wfmt(fmt1, *args)
        else:
            self.wfmt(fmt2, *args)

        self.w('\n')
        if self.time_range == 'day':
            fmt1 = _('Total slacking: {0} ({1} this week, {2} per day)')
            fmt2 = _('Total slacking: {0} ({1} this week)')
        elif self.time_range == 'week':
            fmt1 = _('Total slacking this week: {0} ({1} per day)')
            fmt2 = _('Total slacking this week: {0}')
        elif self.time_range == 'month':
            fmt1 = _('Total slacking this month: {0} ({1} per day)')
            fmt2 = _('Total slacking this month: {0}')
        args = [(format_duration(total_slacking), 'duration')]
        if self.time_range == 'day':
            args.append((format_duration(week_total_slacking), 'duration'))
            per_diem = week_total_slacking / max(1, work_days)
        else:
            per_diem = total_slacking / max(1, work_days)
        if work_days:
            args.append((format_duration(per_diem), 'duration'))
            self.wfmt(fmt1, *args)
        else:
            self.wfmt(fmt2, *args)

        if not self.should_have_extended_footer():
            self._extended_footer = False
            return

        self._extended_footer = True

        if self.hours:
            self.w('\n')
            time_left = self.time_left_at_work(total_work)
            time_to_leave = self.now + time_left
            if time_left < datetime.timedelta(0):
                fmt = _("Time left at work: {0} (should've finished at {1:%H:%M}, overtime of {2} until now)")
                real_time_left = datetime.timedelta(0)
                self.wfmt(
                    fmt,
                    (format_duration(real_time_left), 'duration'),
                    (time_to_leave, 'time'),
                    (format_duration(-time_left), 'duration'),
                )
            else:
                fmt = _('Time left at work: {0} (till {1:%H:%M})')
                self.wfmt(
                    fmt,
                    (format_duration(time_left), 'duration'),
                    (time_to_leave, 'time'),
                )

        if self.office_hours:
            self.w('\n')
            hours = datetime.timedelta(hours=self.office_hours)
            total = total_slacking + total_work
            total += self.get_current_task_time()
            if total > hours:
                self.wfmt(
                    _('At office today: {0} ({1} overtime)'),
                    (format_duration(total), 'duration'),
                    (format_duration(total - hours), 'duration'),
                )
            else:
                self.wfmt(
                    _('At office today: {0} ({1} left)'),
                    (format_duration(total), 'duration'),
                    (format_duration(hours - total), 'duration'),
                )


class ReportView(Gtk.TextView):

    timelog = GObject.Property(
        type=object, default=None, nick='Time log',
        blurb='Time log object')

    name = GObject.Property(
        type=str, nick='Name',
        blurb='Name of report sender')

    sender = GObject.Property(
        type=str, nick='Sender email',
        blurb='Email of the report sender')

    recipient = GObject.Property(
        type=str, nick='Recipient email',
        blurb='Email of the report recipient')

    date = GObject.Property(
        type=object, default=None, nick='Date',
        blurb='Date to show (None tracks today)')

    time_range = GObject.Property(
        type=str, default='day', nick='Time range',
        blurb='Time range to show (day/week/month)')

    report_style = GObject.Property(
        type=str, nick='Report style',
        blurb='Style of the report (plain/categorized)')

    body = GObject.Property(
        type=str, nick='Report body',
        blurb='Report body text')

    report_status = GObject.Property(
        type=str, default='not-sent', nick='Report status',
        blurb='Status of this particular report (not-sent/sent/sent-elsewhere)')

    report_sent_to = GObject.Property(
        type=str, nick='Report was sent to',
        blurb='Who already received this report (other than the current recipient?)')

    def __init__(self):
        Gtk.TextView.__init__(self)
        self._update_pending = False
        self._subject = ''
        self.connect('notify::timelog', self.queue_update)
        self.connect('notify::name', self.update_subject)
        self.connect('notify::date', self.queue_update)
        self.connect('notify::time-range', self.queue_update)
        self.connect('notify::report-style', self.queue_update)
        self.connect('notify::visible', self.queue_update)
        self.connect('notify::recipient', self.update_already_sent_indication)
        self.bind_property('body', self.get_buffer(), 'text',
                           GObject.BindingFlags.BIDIRECTIONAL)
        # GTK+ themes other than Adwaita ignore the 'monospace' property and
        # use a proportional font for text widgets.
        self.override_font(Pango.FontDescription.from_string("Monospace"))

        filename = Settings().get_report_log_file()
        self.record = ReportRecord(filename)

    def queue_update(self, *args):
        if not self._update_pending:
            self._update_pending = True
            GLib.idle_add(self.populate_report)

    def get_time_window(self):
        assert self.timelog is not None
        if self.time_range == 'day':
            return self.timelog.window_for_day(self.date)
        elif self.time_range == 'week':
            return self.timelog.window_for_week(self.date)
        elif self.time_range == 'month':
            return self.timelog.window_for_month(self.date)

    @GObject.Property(type=str, nick='Name', blurb='Report subject')
    def subject(self):
        return self._subject

    def update_subject(self, *args):
        self._subject = ''
        if self.timelog is None or not self.get_visible():
            self.notify('subject')
            return # not loaded yet
        window = self.get_time_window()
        reports = Reports(window)
        name = self.name
        if self.time_range == 'day':
            self._subject = reports.daily_report_subject(name)
        elif self.time_range == 'week':
            self._subject = reports.weekly_report_subject(name)
        elif self.time_range == 'month':
            self._subject = reports.monthly_report_subject(name)
        self.notify('subject')

    def populate_report(self):
        self._update_pending = False
        self.update_subject()
        if self.timelog is None or not self.get_visible():
            self.get_buffer().set_text('')
            return # not loaded yet
        window = self.get_time_window()
        reports = Reports(window, email_headers=False, style=self.report_style)
        output = StringIO()
        recipient = self.recipient
        name = self.name
        if self.time_range == 'day':
            reports.daily_report(output, recipient, name)
        elif self.time_range == 'week':
            reports.weekly_report(output, recipient, name)
        elif self.time_range == 'month':
            reports.monthly_report(output, recipient, name)
        textbuf = self.get_buffer()
        textbuf.set_text(output.getvalue())
        textbuf.place_cursor(textbuf.get_start_iter())
        self.update_already_sent_indication()

    def update_already_sent_indication(self, *args):
        if not self.date:
            return
        report_kind = REPORT_KINDS[self.time_range]
        recipients = self.record.get_recipients(report_kind, self.date)
        self.report_sent_to = ', '.join(sorted(set(recipients) - {self.recipient}))
        if not recipients:
            self.report_status = 'not-sent'
        elif self.recipient in recipients:
            self.report_status = 'sent'
        else:
            self.report_status = 'sent-elsewhere'


class TaskListView(Gtk.TreeView):

    tasks = GObject.Property(
        type=object, nick='Tasks',
        blurb='The task list (an instance of TaskList)')

    def __init__(self):
        Gtk.TreeView.__init__(self)
        self.task_store = Gtk.TreeStore(str, str)
        self.set_model(self.task_store)
        column = Gtk.TreeViewColumn(_('Tasks'), Gtk.CellRendererText(), text=0)
        self.append_column(column)
        self.connect('notify::tasks', self.tasks_changed)

    def get_task_for_row(self, path):
        return self.task_store[path][1]

    def tasks_changed(self, *args):
        mark_time('loading task list')
        self.task_store.clear()
        if self.tasks is None:
            mark_time('task list empty')
            return
        for group_name, group_items in self.tasks.groups:
            if group_name == self.tasks.other_title:
                t = self.task_store.append(None, [_("Other"), ""])
            else:
                t = self.task_store.append(None, [group_name, group_name + ': '])
            for item in group_items:
                if group_name == self.tasks.other_title:
                    task = item
                else:
                    task = group_name + ': ' + item
                self.task_store.append(t, [item, task])
        self.expand_all()
        mark_time('task list loaded')


class PreferencesDialog(Gtk.Dialog):

    use_header_bar = hasattr(Gtk.DialogFlags, 'USE_HEADER_BAR')

    def __init__(self, transient_for, page=None):
        kwargs = {}
        if self.use_header_bar:
            kwargs['use_header_bar'] = True
        Gtk.Dialog.__init__(self, transient_for=transient_for,
                            title=_("Preferences"), **kwargs)
        self.set_default_size(500, 0)

        if not self.use_header_bar:
            self.add_button(_("Close"), Gtk.ResponseType.CLOSE)
            self.set_default_response(Gtk.ResponseType.CLOSE)
        else:
            # can't do it now, it doesn't have window decorations yet!
            GLib.idle_add(self.make_enter_close_the_dialog)

        builder = Gtk.Builder.new_from_file(PREFERENCES_UI_FILE)
        stack = builder.get_object('dialog_stack')
        self.get_content_area().add(stack)
        stack_switcher = Gtk.StackSwitcher(stack=stack)
        self.get_header_bar().set_custom_title(stack_switcher)
        stack_switcher.show()

        if page:
            stack.set_visible_child_name(page)

        virtual_midnight_entry = builder.get_object('virtual_midnight_entry')
        self.virtual_midnight_entry = virtual_midnight_entry

        hours_entry = builder.get_object('hours_entry')
        office_hours_entry = builder.get_object('office_hours_entry')
        name_entry = builder.get_object('name_entry')
        sender_entry = builder.get_object('sender_entry')
        recipient_entry = builder.get_object('recipient_entry')

        protocol_combo = builder.get_object('protocol_combo')
        server_entry = builder.get_object('server_entry')
        port_entry = builder.get_object('port_entry')
        self.port_entry = port_entry
        self.username_entry = builder.get_object('username_entry')
        self.password_entry = builder.get_object('password_entry')

        self.gsettings = Gio.Settings.new("org.gtimelog")
        self.gsettings.bind('hours', hours_entry, 'value', Gio.SettingsBindFlags.DEFAULT)
        self.gsettings.bind('office-hours', office_hours_entry, 'value', Gio.SettingsBindFlags.DEFAULT)
        self.gsettings.bind('name', name_entry, 'text', Gio.SettingsBindFlags.DEFAULT)
        self.gsettings.bind('sender', sender_entry, 'text', Gio.SettingsBindFlags.DEFAULT)
        self.gsettings.bind('list-email', recipient_entry, 'text', Gio.SettingsBindFlags.DEFAULT)
        self.gsettings.connect('changed::virtual-midnight', self.virtual_midnight_changed)
        self.virtual_midnight_changed()
        self.virtual_midnight_entry.connect('focus-out-event', self.virtual_midnight_set)
        self.gsettings.bind('mail-protocol', protocol_combo, 'active-id', Gio.SettingsBindFlags.DEFAULT)
        self.gsettings.bind('smtp-server', server_entry, 'text', Gio.SettingsBindFlags.DEFAULT)
        self.gsettings.connect('changed::smtp-port', self.smtp_port_changed)
        self.gsettings.connect('changed::mail-protocol', self.smtp_port_changed)
        self.smtp_port_changed()
        port_entry.connect('focus-out-event', self.smtp_port_set)
        self.gsettings.bind('smtp-username', self.username_entry, 'text', Gio.SettingsBindFlags.DEFAULT)
        self.refresh_password_field()
        server_entry.connect('focus-out-event', self.refresh_password_field)
        self.username_entry.connect('focus-out-event', self.refresh_password_field)
        self.password_entry.connect('focus-out-event', self.update_password)

    def make_enter_close_the_dialog(self):
        hb = self.get_header_bar()
        hb.forall(self._traverse_headerbar_children, None)

    def _traverse_headerbar_children(self, widget, user_data):
        if isinstance(widget, Gtk.Box):
            widget.forall(self._traverse_headerbar_children, None)
        elif isinstance(widget, Gtk.Button):
            if widget.get_style_context().has_class('close'):
                widget.set_can_default(True)
                widget.grab_default()

    def virtual_midnight_changed(self, *args):
        h, m = self.gsettings.get_value('virtual-midnight')
        self.virtual_midnight_entry.set_text('{:d}:{:02d}'.format(h, m))

    def virtual_midnight_set(self, *args):
        try:
            vm = parse_time(self.virtual_midnight_entry.get_text())
        except ValueError:
            self.virtual_midnight_changed()
        else:
            h, m = self.gsettings.get_value('virtual-midnight')
            if (h, m) != (vm.hour, vm.minute):
                self.gsettings.set_value('virtual-midnight', GLib.Variant('(ii)', (vm.hour, vm.minute)))

    def smtp_port_changed(self, *args):
        port = self.gsettings.get_int('smtp-port')
        if port == 0:
            mail_protocol = self.gsettings.get_string('mail-protocol')
            default_port = MAIL_PROTOCOLS[mail_protocol].factory.default_port
            self.port_entry.set_text('auto (%d)' % default_port)
        else:
            self.port_entry.set_text(str(port))

    def smtp_port_set(self, *args):
        port = self.port_entry.get_text()
        if not port or port.lower().startswith("auto"):
            port = 0
        try:
            port = int(port)
            if not 0 <= port <= 65535:
                raise ValueError('value out of range')
        except ValueError:
            self.smtp_port_changed()
        else:
            self.gsettings.set_int('smtp-port', port)

    def refresh_password_field(self, *args):
        server = self.gsettings.get_string("smtp-server")
        username = self.gsettings.get_string("smtp-username")

        def callback(password):
            # In theory the user could've focused the password field
            # and started typing in a new password, in which case we shouldn't
            # overwrite it!
            self.password_entry.set_text(password)

        if username:
            start_smtp_password_lookup(server, username, callback)
        else:
            self.password_entry.set_text("")

    def update_password(self, *args):
        server = self.gsettings.get_string("smtp-server")
        username = self.gsettings.get_string("smtp-username")
        password = self.password_entry.get_text()
        if username:
            set_smtp_password(server, username, password)


def main():
    mark_time("in main()")

    root_logger = logging.getLogger()
    root_logger.addHandler(logging.StreamHandler())
    if DEBUG:
        root_logger.setLevel(logging.DEBUG)
    else:
        root_logger.setLevel(logging.INFO)

    # Tell Python's gettext.gettext() to use our translations
    gettext.bindtextdomain('gtimelog', LOCALE_DIR)
    gettext.textdomain('gtimelog')

    # Tell GTK+ to use out translations
    if hasattr(locale, 'bindtextdomain'):
        locale.bindtextdomain('gtimelog', LOCALE_DIR)
        locale.textdomain('gtimelog')
    else:  # pragma: nocover
        # https://github.com/gtimelog/gtimelog/issues/95#issuecomment-252299266
        # locale.bindtextdomain is missing on Windows!
        log.error(_("Unable to configure translations: no locale.bindtextdomain()"))

    # Make ^C terminate the process
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # Run the app
    app = Application()
    mark_time("app created")
    try:
        sys.exit(app.run(sys.argv))
    finally:
        mark_time("exiting")


if __name__ == '__main__':
    main()
