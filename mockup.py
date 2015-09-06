#!/usr/bin/python3
from __future__ import print_function

import time
import os
DEBUG = os.getenv('DEBUG')


def mark_time(what=None, _prev=[0, 0]):
    t = time.time()
    if DEBUG:
        if what:
            print("{:.3f} ({:+.3f}) {}".format(t - _prev[1], t - _prev[0], what))
        else:
            print()
            _prev[1] = t
    _prev[0] = t

mark_time()
mark_time("in script")

import datetime
import gettext
import locale
import re
import signal
import sys
from gettext import gettext as _

mark_time("Python imports done")


import gi
mark_time("gi import done")
gi.require_version('Gtk', '3.0')
mark_time("gi.require_version done")

from gi.repository import GLib
mark_time("GLib import done")
from gi.repository import GObject
mark_time("GObject import done")
from gi.repository import Gio
mark_time("Gio import done")
from gi.repository import Gdk
mark_time("Gdk import done")
from gi.repository import Gtk
mark_time("Gtk import done")
from gi.repository import Pango
mark_time("Pango import done")

pkgdir = os.path.join(os.path.dirname(__file__), 'src')
sys.path.insert(0, pkgdir)

from gtimelog.settings import Settings
from gtimelog.timelog import (
    as_minutes, virtual_day, different_days, prev_month, next_month, uniq)

mark_time("gtimelog imports done")

HELP_URL = 'https://mg.pov.lt/gtimelog'

UI_FILE = 'src/gtimelog/experiment.ui'
ABOUT_DIALOG_UI_FILE = 'src/gtimelog/about.ui'
MENUS_UI_FILE = 'src/gtimelog/menus.ui'
CSS_FILE = 'src/gtimelog/gtimelog.css'
LOCALE_DIR = 'locale'


def format_duration(duration):
    """Format a datetime.timedelta with minute precision.

    The difference from gtimelog.timelog.format_duration() is that this
    one is internationalized.
    """
    h, m = divmod(as_minutes(duration), 60)
    return _('{0} h {1} min').format(h, m)


class Application(Gtk.Application):

    def __init__(self):
        super(Application, self).__init__(application_id='lt.pov.mg.gtimelog_mockup')
        GLib.set_application_name(_("Time Log"))
        GLib.set_prgname('gtimelog')

    def do_startup(self):
        mark_time("in app startup")
        Gtk.Application.do_startup(self)

        mark_time("basic app startup done")
        css = Gtk.CssProvider()
        css.load_from_path(CSS_FILE)
        screen = Gdk.Screen.get_default()
        Gtk.StyleContext.add_provider_for_screen(
            screen, css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        mark_time("CSS loaded")

        builder = Gtk.Builder.new_from_file(MENUS_UI_FILE)
        self.set_app_menu(builder.get_object('app_menu'))
        mark_time("menus loaded")

        for action_name in ['help', 'about', 'quit', 'edit-log']:
            action = Gio.SimpleAction.new(action_name, None)
            action.connect('activate', getattr(self, 'on_' + action_name.replace('-', '_')))
            self.add_action(action)

        self.set_accels_for_action("win.detail-level::chronological", ["<Alt>1"])
        self.set_accels_for_action("win.detail-level::grouped", ["<Alt>2"])
        self.set_accels_for_action("win.detail-level::summary", ["<Alt>3"])
        self.set_accels_for_action("win.time-range::day", ["<Alt>4"])
        self.set_accels_for_action("win.time-range::week", ["<Alt>5"])
        self.set_accels_for_action("win.time-range::month", ["<Alt>6"])
        self.set_accels_for_action("win.show-task-pane", ["F9"])
        self.set_accels_for_action("win.go-back", ["<Alt>Left"])
        self.set_accels_for_action("win.go-forward", ["<Alt>Right"])
        self.set_accels_for_action("win.go-home", ["<Alt>Home"])
        self.set_accels_for_action("app.edit-log", ["<Primary>E"])
        self.set_accels_for_action("app.quit", ["<Primary>Q"])
        self.set_accels_for_action("win.send-report", ["<Primary>D"])

        mark_time("app startup done")

    def on_quit(self, action, parameter):
        self.quit()

    def on_edit_log(self, action, parameter):
        filename = Settings().get_timelog_file()
        uri = GLib.filename_to_uri(filename, None)
        Gtk.show_uri(None, uri, Gdk.CURRENT_TIME)

    def on_help(self, action, parameter):
        Gtk.show_uri(None, HELP_URL, Gdk.CURRENT_TIME)

    def on_about(self, action, parameter):
        # Note: must create a new dialog (which means a new Gtk.Builder)
        # on every invocation.
        builder = Gtk.Builder.new_from_file(ABOUT_DIALOG_UI_FILE)
        about_dialog = builder.get_object('about_dialog')
        about_dialog.set_transient_for(self.get_active_window())
        about_dialog.connect("response", lambda *args: about_dialog.destroy())
        about_dialog.show()

    def do_activate(self):
        mark_time("in app activate")
        if self.get_active_window() is not None:
            self.get_active_window().present()
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
    blacklist = ('events', 'child', 'parent', 'input-hints', 'buffer', 'tabs', 'completion', 'model')
    for prop in src.props:
        if prop.flags & GObject.ParamFlags.DEPRECATED != 0:
            continue
        if prop.flags & GObject.ParamFlags.READWRITE != GObject.ParamFlags.READWRITE:
            continue
        if prop.name in blacklist:
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

    class Actions(object):

        def __init__(self, win, builder):
            self.detail_level = Gio.PropertyAction.new("detail-level", win, "detail-level")
            win.add_action(self.detail_level)

            self.time_range = Gio.PropertyAction.new("time-range", win, "time-range")
            win.add_action(self.time_range)

            self.show_task_pane = Gio.PropertyAction.new("show-task-pane", builder.get_object("task_pane"), "visible")
            win.add_action(self.show_task_pane)

            for action_name in ['go-back', 'go-forward', 'go-home', 'add-entry']:
                action = Gio.SimpleAction.new(action_name, None)
                action.connect('activate', getattr(win, 'on_' + action_name.replace('-', '_')))
                win.add_action(action)
                setattr(self, action_name.replace('-', '_'), action)

    def __init__(self, app):
        Gtk.ApplicationWindow.__init__(self, application=app, icon_name='gtimelog')

        self._watches = []
        self._date = None
        self._showing_today = None
        self.timelog = None
        self.tasks = None

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
        main_box = builder.get_object('main_box')
        headerbar = builder.get_object('headerbar')
        main_window.set_titlebar(None)
        main_window.remove(main_box)
        main_window.destroy()
        self.add(main_box)
        self.set_titlebar(headerbar)
        self.set_default_size(800, 500)
        self.props.window_position = Gtk.WindowPosition.CENTER

        # Cannot store these in the same .ui file nor hook them up in the
        # .ui because glade doesn't support that and strips both the
        # <menu> and the menu-model property on save.
        builder.get_object('menu_button').set_menu_model(builder.get_object('window_menu'))
        builder.get_object('view_button').set_menu_model(builder.get_object('view_menu'))

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
        self.bind_property('title', self.headerbar, 'subtitle', GObject.BindingFlags.DEFAULT)

        self.task_list = TaskList()
        swap_widget(builder, 'task_list', self.task_list)
        self.task_list.connect('row-activated', self.task_list_row_activated)
        self.bind_property('tasks', self.task_list, 'tasks', GObject.BindingFlags.DEFAULT)

        self.actions = self.Actions(self, builder)
        self.actions.add_entry.set_enabled(False)

        mark_time('window created')

        self.settings = Settings()
        self.settings.load()
        self.log_view.hours = self.settings.hours
        self.log_view.office_hours = self.settings.hours
        mark_time('settings loaded')

        self.date = None  # initialize today's date

        self.task_entry.connect('changed', self.task_entry_changed)
        self.connect('notify::detail-level', self.detail_level_changed)
        self.connect('notify::time-range', self.time_range_changed)
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

    def load_log(self):
        mark_time("loading timelog")
        timelog = self.settings.get_time_log()
        mark_time("timelog loaded")
        self.timelog = timelog
        self.tick(True)
        self.enable_add_entry()
        mark_time("timelog presented")
        self.watch_file(self.timelog.filename, self.on_timelog_file_changed)

    def load_tasks(self):
        mark_time("loading tasks")
        tasks = self.settings.get_task_list()
        mark_time("tasks loaded")
        self.tasks = tasks
        mark_time("tasks presented")
        self.watch_file(self.tasks.filename, self.on_tasks_file_changed)

    def watch_file(self, filename, callback):
        gf = Gio.File.new_for_path(filename)
        gfm = gf.monitor_file(Gio.FileMonitorFlags.NONE, None)
        gfm.connect('changed', callback)
        self._watches.append(gfm) # keep a reference so it doesn't get garbage collected

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
        today = virtual_day(datetime.datetime.now(), self.settings.virtual_midnight)
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
            self.notify('title')

    @GObject.Property(
        type=bool, default=True, nick='Showing today',
        blurb='Currently visible time range includes today')
    def showing_today(self):
        return self._showing_today

    @GObject.Property(
        type=str, nick='Title',
        blurb='Description of the visible time range')
    def title(self):
        date = self.date
        if not date:
            return ''
        if self.time_range == 'day':
            return _("{0:%A, %Y-%m-%d} (week {1:0>2})").format(
                date, date.isocalendar()[1])
        elif self.time_range == 'week':
            return _("{0:%Y}, week {1:0>2} ({0:%B %-d}-{2:%-d})").format(
                date, date.isocalendar()[1], date + datetime.timedelta(6))
        elif self.time_range == 'month':
            return _("{0:%B %Y}").format(date)

    def detail_level_changed(self, obj, param_spec):
        assert self.detail_level in {'chronological', 'grouped', 'summary'}
        self.notify('title')

    def time_range_changed(self, obj, param_spec):
        assert self.time_range in {'day', 'week', 'month'}
        self.notify('title')

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
        self.task_entry.set_text('')
        self.task_entry.grab_focus()
        mark_time("focus grabbed")
        self.tick(True)
        mark_time("label updated")

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
        if event_type == Gio.FileMonitorEvent.CHANGES_DONE_HINT:
            self.check_reload()
        else:
            GLib.timeout_add_seconds(1, self.check_reload)

    def on_tasks_file_changed(self, monitor, file, other_file, event_type):
        if event_type == Gio.FileMonitorEvent.CHANGES_DONE_HINT:
            self.check_reload_tasks()
        else:
            GLib.timeout_add_seconds(1, self.check_reload_tasks)

    def check_reload(self):
        if self.timelog.check_reload():
            self.notify('timelog')
            self.tick(True)

    def check_reload_tasks(self):
        if self.tasks.check_reload():
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
        GObject.idle_add(self._focus_task_entry)

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
        return True


class TaskEntry(Gtk.Entry):

    timelog = GObject.Property(
        type=object, default=None, nick='Time log',
        blurb='Time log object')

    completion_limit = GObject.Property(
        type=int, default=1000, nick='Completion limit',
        blurb='Maximum number of items in the completion popup')

    def __init__(self):
        Gtk.Entry.__init__(self)
        self.set_up_history()
        self.set_up_completion()
        self.connect('notify::timelog', self.timelog_changed)
        self.connect('notify::completion-limit', self.timelog_changed)
        self.connect('changed', self.on_changed)

    def set_up_history(self):
        self.history = []
        self.filtered_history = []
        self.history_pos = 0
        self.history_undo = ''

    def set_up_completion(self):
        completion = Gtk.EntryCompletion()
        self.completion_choices = Gtk.ListStore(str)
        self.completion_choices_as_set = set()
        completion.set_model(self.completion_choices)
        completion.set_text_column(0)
        self.set_completion(completion)

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
                l for l in self.history if l.startswith(self.history_undo)])
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

    hours = GObject.Property(
        type=int, default=0, nick='Hours',
        blurb='Target number of work hours per day')

    office_hours = GObject.Property(
        type=int, default=0, nick='Office Hours',
        blurb='Target number of office hours per day')

    current_task = GObject.Property(
        type=str, nick='Current task',
        blurb='Current task in progress')

    now = GObject.Property(
        type=object, default=None, nick='Now',
        blurb='Current date and time')

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
        self.connect('notify::hours', self.queue_footer_update)
        self.connect('notify::office-hours', self.queue_footer_update)
        self.connect('notify::current-task', self.queue_footer_update)
        self.connect('notify::now', self.queue_footer_update)

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
        return self.now - self.get_last_time()

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
        if self.detail_level == 'chronological':
            prev = None
            for item in window.all_entries():
                first_of_day = prev is None or different_days(prev, item.start, self.timelog.virtual_midnight)
                if first_of_day and prev is not None:
                    self.w("\n")
                if self.time_range != 'day' and first_of_day:
                    self.w(_("{0:%A, %Y-%m-%d}\n").format(item.start))
                self.write_item(item)
                prev = item.start
        elif self.detail_level == 'grouped':
            work, slack = window.grouped_entries()
            for start, entry, duration in work + slack:
                self.write_group(entry, duration)
        elif self.detail_level == 'summary':
            entries, totals = window.categorized_work_entries()
            no_cat = totals.pop(None, None)
            if no_cat is not None:
                self.write_group('no category', no_cat)
            for category, duration in sorted(totals.items()):
                self.write_group(category, duration)
        else:
            return # bug!
        self.reposition_cursor()
        self.add_footer()
        self.scroll_to_end()

    def entry_added(self, same_day):
        if self.detail_level == 'chronological' and same_day:
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
        # If I do the scrolling immediatelly, it won't scroll to the end, usually.
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
        for bit in re.split('({\d+(?::[^}]*)?})', fmt):
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
                time_left = datetime.timedelta(0)
            self.wfmt(
                _('Time left at work: {0} (till {1:%H:%M})'),
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


class TaskList(Gtk.TreeView):

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


def main():
    mark_time("in main()")
    # Tell GTK+ to use out translations
    locale.bindtextdomain('gtimelog', LOCALE_DIR)
    locale.textdomain('gtimelog')
    # Tell Python's gettext.gettext() to use our translations
    gettext.bindtextdomain('gtimelog', LOCALE_DIR)
    gettext.textdomain('gtimelog')

    # Make ^C terminate the process
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # Run the app
    app = Application()
    mark_time("app created")
    sys.exit(app.run(sys.argv))


if __name__ == '__main__':
    main()
