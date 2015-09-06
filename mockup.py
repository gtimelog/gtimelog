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
    as_minutes, virtual_day, different_days, prev_month, next_month)

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

        mark_time("loading CSS")
        css = Gtk.CssProvider()
        css.load_from_path(CSS_FILE)
        screen = Gdk.Screen.get_default()
        Gtk.StyleContext.add_provider_for_screen(
            screen, css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        mark_time("loading menus")
        builder = Gtk.Builder.new_from_file(MENUS_UI_FILE)
        mark_time("menus loaded")
        self.set_app_menu(builder.get_object('app_menu'))

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


class Window(Gtk.ApplicationWindow):

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

        self.timelog = None
        self._extended_footer = False

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
        self.task_entry = builder.get_object('task_entry')
        self.task_entry.grab_focus() # I specified this in the .ui file but it gets ignored
        self.add_button = builder.get_object('add_button')
        self.add_button.props.has_default = True # I specified this in the .ui file but it gets ignored
        self.log_view = builder.get_object('log_view')
        self.set_up_log_view_columns()
        self.log_buffer = self.log_view.get_buffer()
        self.log_buffer.create_tag('today', foreground='#204a87')     # Tango dark blue
        self.log_buffer.create_tag('duration', foreground='#ce5c00')  # Tango dark orange
        self.log_buffer.create_tag('time', foreground='#4e9a06')      # Tango dark green
        self.log_buffer.create_tag('slacking', foreground='gray')

        self.actions = self.Actions(self, builder)
        self.actions.add_entry.set_enabled(False)

        mark_time('window created')

        self.settings = Settings()
        self.settings.load()
        mark_time('settings loaded')

        self.date = None  # initialize today's date

        self.task_entry.connect('changed', self.task_entry_changed)
        self.connect('notify::detail-level', self.detail_level_changed)
        self.connect('notify::time-range', self.time_range_changed)
        mark_time('window ready')

        GLib.idle_add(self.load_log)
        self.tick(True)
        # In theory we could wake up once every 60 seconds.  Shame that
        # there's no timeout_add_minutes.  I don't want to use
        # timeout_add_seconds(60) because that wouldn't be aligned to a
        # minute boundary, so we would delay updating the current time
        # unnecessarily.
        GLib.timeout_add_seconds(1, self.tick)

    def set_up_log_view_columns(self):
        """Set up tab stops in the log view."""
        # we can't get a Pango context for unrealized widgets
        self.log_view.realize()
        pango_context = self.log_view.get_pango_context()
        em = pango_context.get_font_description().get_size()
        tabs = Pango.TabArray.new(2, False)
        tabs.set_tab(0, Pango.TabAlign.LEFT, 9 * em)
        tabs.set_tab(1, Pango.TabAlign.LEFT, 12.5 * em)
        self.log_view.set_tabs(tabs)

    def load_log(self):
        mark_time("loading timelog")
        self.timelog = self.settings.get_time_log()
        mark_time("timelog loaded")
        self.populate_log()
        self.tick(True)
        self.enable_add_entry()
        mark_time("timelog presented")
        gf = Gio.File.new_for_path(self.timelog.filename)
        gfm = gf.monitor_file(Gio.FileMonitorFlags.NONE, None)
        gfm.connect('changed', self.on_timelog_file_changed)
        self._gfm = gfm  # keep a reference so it doesn't get garbage collected

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

    def get_subtitle(self):
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

    def get_now(self):
        return datetime.datetime.now().replace(second=0, microsecond=0)

    def get_current_task(self):
        """Return the current task entry text (as Unicode)."""
        entry = self.task_entry.get_text()
        if isinstance(entry, bytes):
            entry = entry.decode('UTF-8')
        return entry

    def get_current_task_time(self, now=None):
        last_time = self.get_last_time()
        if last_time is None:
            return datetime.timedelta(0)
        if now is None:
            now = self.get_now()
        current_task_time = now - last_time
        return current_task_time

    def get_current_task_work_time(self, now=None):
        current_task = self.get_current_task()
        if '**' in current_task:
            return datetime.timedelta(0)
        else:
            return self.get_current_task_time(now)

    def time_left_at_work(self, total_work, now=None):
        """Calculate time left to work."""
        total_time = total_work + self.get_current_task_work_time(now)
        return datetime.timedelta(hours=self.settings.hours) - total_time

    @property
    def showing_today(self):
        return self._showing_today

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

        self._date = new_date

        if new_date == today:
            self._showing_today = True
            self.actions.go_home.set_enabled(False)
            self.actions.go_forward.set_enabled(False)
        else:
            self._showing_today = False
            self.actions.go_home.set_enabled(True)
            self.actions.go_forward.set_enabled(True)

        self.populate_log()

    def detail_level_changed(self, obj, param_spec):
        assert self.detail_level in {'chronological', 'grouped', 'summary'}
        self.populate_log()

    def time_range_changed(self, obj, param_spec):
        assert self.time_range in {'day', 'week', 'month'}
        self.populate_log()

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
        if self.detail_level == 'chronological' and same_day:
            self.delete_footer()
            self.write_item(self.timelog.last_entry())
            self.add_footer()
            self.scroll_to_end()
            mark_time("optimized update done")
        else:
            self.populate_log()
            mark_time("populate_log done")
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

    def check_reload(self):
        if self.timelog.check_reload():
            self.populate_log()
            self.tick(True)

    def enable_add_entry(self):
        enabled = self.timelog is not None and self.get_current_task().strip()
        self.actions.add_entry.set_enabled(enabled)

    def task_entry_changed(self, widget):
        self.enable_add_entry()
        if self._extended_footer:
            # Update "time left to work" in case we added/deleted '**'
            self.delete_footer()
            self.add_footer()

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
            if self._extended_footer:
                # Update "time left to work"
                self.delete_footer()
                self.add_footer()
        return True

    def populate_log(self):
        self.headerbar.set_subtitle(self.get_subtitle())
        self.log_buffer.set_text('')
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

    def reposition_cursor(self):
        where = self.log_buffer.get_end_iter()
        where.backward_cursor_position()
        self.log_buffer.place_cursor(where)

    def scroll_to_end(self):
        # XXX: seems to be buggy: switch to a month view and add a new
        # entry -- it will scroll a bit, but not to the very end
        buffer = self.log_view.get_buffer()
        end_mark = buffer.create_mark('end', buffer.get_end_iter())
        self.log_view.scroll_to_mark(end_mark, 0, False, 0, 0)
        buffer.delete_mark(end_mark)

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
        buffer = self.log_buffer
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

    def delete_footer(self):
        buffer = self.log_buffer
        buffer.delete(
            buffer.get_iter_at_mark(self.footer_mark), buffer.get_end_iter())
        buffer.delete_mark(self.footer_mark)
        self.footer_mark = None

    def add_footer(self):
        buffer = self.log_buffer
        self.footer_mark = buffer.create_mark(
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

        if not self.showing_today or self.time_range != 'day':
            self._extended_footer = False
            return

        self._extended_footer = True

        now = self.get_now()
        time_left = self.time_left_at_work(total_work, now)
        if time_left is not None:
            self.w('\n')
            time_to_leave = now + time_left
            if time_left < datetime.timedelta(0):
                time_left = datetime.timedelta(0)
            self.wfmt(
                _('Time left at work: {0} (till {1:%H:%M})'),
                (format_duration(time_left), 'duration'),
                (time_to_leave, 'time'),
            )

        if self.settings.show_office_hours:
            self.w('\n')
            hours = datetime.timedelta(hours=self.settings.hours)
            total = total_slacking + total_work
            total += self.get_current_task_time(now)
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
