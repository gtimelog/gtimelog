import datetime
import functools
import logging
import os
import smtplib
from contextlib import closing
from email.utils import parseaddr
from gettext import gettext as _
from gi.repository import Gtk, Gdk, GLib, Gio, GObject, Soup

from gtimelog import DEBUG
from gtimelog.core.exceptions import EmailError
from gtimelog.ui.components.services import start_smtp_password_lookup, Authenticator
from gtimelog.core.settings import Settings
from gtimelog.core.tasks import TaskList
from gtimelog.core.time import TimeLog
from gtimelog.core.utils import mark_time, prev_month, prepare_message, virtual_day, next_month
from gtimelog.paths import UI_FILE, MENUS_UI_FILE
from gtimelog.ui.components.entries import TaskEntry
from gtimelog.ui.components.utils import copy_properties, swap_widget, internationalised_format_duration, \
    MAIL_PROTOCOLS, REPORT_KINDS
from gtimelog.ui.components.views import LogView, TaskListView, ReportView

log = logging.getLogger(__name__)
soup_session = Soup.SessionAsync()
authenticator = Authenticator(soup_session)
soup_session.connect('authenticate', authenticator.http_auth_cb)


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

    filter_text = GObject.Property(
        type=str, default='', nick='Filter text',
        blurb='Show only tasks matching this substring')

    class Actions(object):

        def __init__(self, win):
            PropertyAction = Gio.PropertyAction

            self.detail_level = PropertyAction.new("detail-level", win, "detail-level")
            win.add_action(self.detail_level)

            self.time_range = PropertyAction.new("time-range", win, "time-range")
            win.add_action(self.time_range)

            self.show_view_menu = PropertyAction.new("show-view-menu", win.view_button, "active")
            win.add_action(self.show_view_menu)

            self.show_task_pane = PropertyAction.new("show-task-pane", win.task_pane, "visible")
            win.add_action(self.show_task_pane)

            self.show_menu = PropertyAction.new("show-menu", win.menu_button, "active")
            win.add_action(self.show_menu)

            self.show_search_bar = PropertyAction.new("show-search-bar", win.search_bar, "search-mode-enabled")
            win.add_action(self.show_search_bar)

            for action_name in ['go-back', 'go-forward', 'go-home', 'add-entry', 'report', 'send-report', 'cancel-report']:
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
        self.task_entry.bind_property('text', self.log_view, 'current_task', GObject.BindingFlags.DEFAULT)
        self.bind_property('subtitle', self.headerbar, 'subtitle', GObject.BindingFlags.DEFAULT)
        self.bind_property('filter_text', self.log_view, 'filter_text', GObject.BindingFlags.DEFAULT)

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
            old_settings.load()
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
            old_message, old_url = self._download
            soup_session.cancel_message(old_message, Soup.Status.CANCELLED)
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
        self.tasks_infobar.connect('response', lambda *args: self.cancel_tasks_download())
        self.tasks_infobar.show()
        self.tasks_infobar.queue_resize()
        log.debug("Downloading tasks from %s", url)
        message = Soup.Message.new('GET', url)
        self._download = (message, url)
        soup_session.queue_message(message, self.tasks_downloaded, cache_filename)

    def tasks_downloaded(self, session, message, cache_filename):
        content = message.response_body.data
        if message.status_code != Soup.Status.OK:
            url = message.get_uri().to_string(just_path_and_query=False)

            log.error("Failed to download tasks from %s: %d %s", url, message.status_code, message.reason_phrase)
            self.tasks_infobar.set_message_type(Gtk.MessageType.ERROR)
            self.tasks_infobar_label.set_text(_("Download failed."))
            self.tasks_infobar.connect('response', lambda *args: self.tasks_infobar.hide())
            self.tasks_infobar.show()
        else:
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
            self.time_label.set_text(internationalised_format_duration(now - last_time))
        self.log_view.now = now
        if self.showing_today and virtual_day(now, self.get_virtual_midnight()) != self.date:
            self.date = None
        return True
