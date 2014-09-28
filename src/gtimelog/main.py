"""An application for keeping track of your time."""

# Default to new-style classes.
__metaclass__ = type

import os
import re
import sys
import errno
import codecs
import signal
import logging
import datetime
import optparse
import tempfile

import gtimelog


log = logging.getLogger('gtimelog')


try:
    unicode
except NameError:
    unicode = str


# Which Gnome toolkit should we use?  Prior to 0.7, pygtk was the default with
# a fallback to gi (gobject introspection), except on Ubuntu where gi was
# forced.  With 0.7, gi was made the default in upstream, so the Ubuntu
# specific patch isn't necessary.

if '--prefer-pygtk' in sys.argv:
    sys.argv.remove('--prefer-pygtk')
    try:
        import pygtk
        toolkit = 'pygtk'
    except ImportError:
        try:
            import gi
            toolkit = 'gi'
        except ImportError:
            sys.exit("Please install pygobject or pygtk")
else:
    try:
        import gi
        toolkit = 'gi'
    except ImportError:
        try:
            import pygtk
            toolkit = 'pygtk'
        except ImportError:
            sys.exit("Please install pygobject or pygtk")


if toolkit == 'gi':
    from gi.repository import GObject as gobject
    from gi.repository import Gdk as gdk
    from gi.repository import Gtk as gtk
    from gi.repository import Pango as pango
    # These are hacks until we fully switch to GI.
    try:
        PANGO_ALIGN_LEFT = pango.TabAlign.LEFT
    except AttributeError:
        # Backwards compatible for older Pango versions with broken GIR.
        PANGO_ALIGN_LEFT = pango.TabAlign.TAB_LEFT
    GTK_RESPONSE_OK = gtk.ResponseType.OK
    gtk_status_icon_new = gtk.StatusIcon.new_from_file
    pango_tabarray_new = pango.TabArray.new

    if gtk._version.startswith('2'):
        gtk_version = 2
    else:
        gtk_version = 3

    try:
        if gtk._version.startswith('2'):
            from gi.repository import AppIndicator
        else:
            from gi.repository import AppIndicator3 as AppIndicator
        new_app_indicator = AppIndicator.Indicator.new
        APPINDICATOR_CATEGORY = (
            AppIndicator.IndicatorCategory.APPLICATION_STATUS)
        APPINDICATOR_ACTIVE = AppIndicator.IndicatorStatus.ACTIVE
    except (ImportError, gi._gi.RepositoryError):
        new_app_indicator = None
else:
    pygtk.require('2.0')
    import gobject
    import gtk
    from gtk import gdk as gdk
    import pango

    gtk_version = 2
    PANGO_ALIGN_LEFT = pango.TAB_LEFT
    GTK_RESPONSE_OK = gtk.RESPONSE_OK
    gtk_status_icon_new = gtk.status_icon_new_from_file
    pango_tabarray_new = pango.TabArray

    try:
        import appindicator
        new_app_indicator = appindicator.Indicator
        APPINDICATOR_CATEGORY = appindicator.CATEGORY_APPLICATION_STATUS
        APPINDICATOR_ACTIVE = appindicator.STATUS_ACTIVE
    except ImportError:
        # apt-get install python-appindicator on Ubuntu
        new_app_indicator = None

try:
    import dbus
    import dbus.service
    import dbus.mainloop.glib
except ImportError:
    dbus = None

from gtimelog import __version__


# This is to let people run GTimeLog without having to install it
resource_dir = os.path.dirname(os.path.realpath(__file__))
ui_file = os.path.join(resource_dir, "gtimelog.ui")
icon_file_bright = os.path.join(resource_dir, "gtimelog-small-bright.png")
icon_file_dark = os.path.join(resource_dir, "gtimelog-small.png")

# This is for distribution packages
if not os.path.exists(ui_file):
    ui_file = "/usr/share/gtimelog/gtimelog.ui"
if not os.path.exists(icon_file_dark):
    icon_file_dark = "/usr/share/pixmaps/gtimelog-small.png"
if not os.path.exists(icon_file_bright):
    icon_file_bright = "/usr/share/pixmaps/gtimelog-small-bright.png"


from gtimelog.settings import Settings
from gtimelog.timelog import (
    format_duration, format_duration_short, uniq,
    Reports, TimeLog, TaskList, RemoteTaskList)


class IconChooser:

    @property
    def icon_name(self):
        # XXX assumes the panel's color matches a menu bar's color, which is
        # not necessarily the case!  this logic works for, say,
        # Ambiance/Radiance, but it gets New Wave and Dark Room wrong.
        if toolkit == 'gi':
            menu_bar = gtk.MenuBar()
            # need to hold a reference to menu_bar to avoid LP#1016212
            style = menu_bar.get_style_context()
            color = style.get_color(gtk.StateFlags.NORMAL)
            value = (color.red + color.green + color.blue) / 3
        else:
            style = gtk.MenuBar().rc_get_style()
            color = style.text[gtk.STATE_NORMAL]
            value = color.value
        filename = icon_file_bright if value >= 0.5 else icon_file_dark
        log.debug('Menu bar color: (%g, %g, %g), averages to %g; picking %s',
                  color.red, color.green, color.blue, value, filename)
        return filename


class SimpleStatusIcon(IconChooser):
    """Status icon for gtimelog in the notification area."""

    def __init__(self, gtimelog_window):
        self.gtimelog_window = gtimelog_window
        self.timelog = gtimelog_window.timelog
        self.trayicon = None
        if not hasattr(gtk, 'StatusIcon'):
            # You must be using a very old PyGtk.
            return
        self.icon = gtk_status_icon_new(self.icon_name)
        self.last_tick = False
        self.tick()
        self.icon.connect('activate', self.on_activate)
        self.icon.connect('popup-menu', self.on_popup_menu)
        if gtk_version == 2:
            self.gtimelog_window.main_window.connect(
                'style-set', self.on_style_set)
        else: # assume Gtk+ 3
            self.gtimelog_window.main_window.connect(
                'style-updated', self.on_style_set)
        gobject.timeout_add_seconds(1, self.tick)
        self.gtimelog_window.entry_watchers.append(self.entry_added)
        self.gtimelog_window.tray_icon = self

    def available(self):
        """Is the icon supported by this system?

        SimpleStatusIcon needs PyGtk 2.10 or newer
        """
        return self.icon is not None

    def on_style_set(self, *args):
        """The user chose a different theme."""
        self.icon.set_from_file(self.icon_name)

    def on_activate(self, widget):
        """The user clicked on the icon."""
        self.gtimelog_window.toggle_visible()

    def on_popup_menu(self, widget, button, activate_time):
        """The user clicked on the icon."""
        tray_icon_popup_menu = self.gtimelog_window.tray_icon_popup_menu
        if toolkit == "gi":
            tray_icon_popup_menu.popup(
                None, None, gtk.StatusIcon.position_menu,
                self.icon, button, activate_time)
        else:
            tray_icon_popup_menu.popup(
                None, None, gtk.status_icon_position_menu,
                button, activate_time, self.icon)

    def entry_added(self, entry):
        """An entry has been added."""
        self.tick()

    def tick(self):
        """Tick every second."""
        self.icon.set_tooltip_text(self.tip())
        return True

    def tip(self):
        """Compute tooltip text."""
        # NB: returns UTF-8 text instead of Unicode on Python 2.  This
        # seems to be harmless for now.
        current_task = self.gtimelog_window.task_entry.get_text()
        if not current_task:
            current_task = 'nothing'
        tip = 'GTimeLog: working on {0}'.format(current_task)
        total_work, total_slacking = self.timelog.window.totals()
        tip += '\nWork done today: {0}'.format(format_duration(total_work))
        time_left = self.gtimelog_window.time_left_at_work(total_work)
        if time_left is not None:
            if time_left < datetime.timedelta(0):
                time_left = datetime.timedelta(0)
            tip += '\nTime left at work: {0}'.format(
                format_duration(time_left))
        return tip


class AppIndicator(IconChooser):
    """Ubuntu's application indicator for gtimelog."""

    # XXX: on Ubuntu 10.04 the app indicator apparently doesn't understand
    # set_icon('/absolute/path'), and so gtimelog ends up being without an
    # icon.  I don't know if I want to continue supporting Ubuntu 10.04.

    def __init__(self, gtimelog_window):
        self.gtimelog_window = gtimelog_window
        self.timelog = gtimelog_window.timelog
        self.indicator = None
        if new_app_indicator is None:
            return
        self.indicator = new_app_indicator(
            'gtimelog', self.icon_name, APPINDICATOR_CATEGORY)
        self.indicator.set_status(APPINDICATOR_ACTIVE)
        self.indicator.set_menu(gtimelog_window.app_indicator_menu)
        self.gtimelog_window.tray_icon = self
        if gtk_version == 2:
            self.gtimelog_window.main_window.connect(
                'style-set', self.on_style_set)
        else: # assume Gtk+ 3
            self.gtimelog_window.main_window.connect(
                'style-updated', self.on_style_set)

    def available(self):
        """Is the icon supported by this system?

        AppIndicator needs python-appindicator
        """
        return self.indicator is not None

    def on_style_set(self, *args):
        """The user chose a different theme."""
        self.indicator.set_icon(self.icon_name)


class OldTrayIcon(IconChooser):
    """Old tray icon for gtimelog, shows a ticking clock.

    Uses the old and deprecated egg.trayicon module.
    """

    def __init__(self, gtimelog_window):
        self.gtimelog_window = gtimelog_window
        self.timelog = gtimelog_window.timelog
        self.trayicon = None
        try:
            import egg.trayicon
        except ImportError:
            # Nothing to do here, move along or install python-gnome2-extras
            # which was later renamed to python-eggtrayicon.
            return
        self.eventbox = gtk.EventBox()
        hbox = gtk.HBox()
        self.icon = gtk.Image()
        self.icon.set_from_file(self.icon_name)
        hbox.add(self.icon)
        self.time_label = gtk.Label()
        hbox.add(self.time_label)
        self.eventbox.add(hbox)
        self.trayicon = egg.trayicon.TrayIcon('GTimeLog')
        self.trayicon.add(self.eventbox)
        self.last_tick = False
        self.tick(force_update=True)
        self.trayicon.show_all()
        if gtk_version == 2:
            self.gtimelog_window.main_window.connect(
                'style-set', self.on_style_set)
        else: # assume Gtk+ 3
            self.gtimelog_window.main_window.connect(
                'style-updated', self.on_style_set)
        tray_icon_popup_menu = gtimelog_window.tray_icon_popup_menu
        self.eventbox.connect_object(
            'button-press-event', self.on_press, tray_icon_popup_menu)
        self.eventbox.connect('button-release-event', self.on_release)
        gobject.timeout_add_seconds(1, self.tick)
        self.gtimelog_window.entry_watchers.append(self.entry_added)
        self.gtimelog_window.tray_icon = self

    def available(self):
        """Is the icon supported by this system?

        OldTrayIcon needs egg.trayicon, which is now deprecated and likely
        no longer available in modern Linux distributions.
        """
        return self.trayicon is not None

    def on_style_set(self, *args):
        """The user chose a different theme."""
        self.icon.set_from_file(self.icon_name)

    def on_press(self, widget, event):
        """A mouse button was pressed on the tray icon label."""
        if event.button != 3:
            return
        main_window = self.gtimelog_window.main_window
        # This should be unnecessary, as we now show/hide menu items
        # immediatelly after showing/hiding the main window.
        if main_window.get_property('visible'):
            self.gtimelog_window.tray_show.hide()
            self.gtimelog_window.tray_hide.show()
        else:
            self.gtimelog_window.tray_show.show()
            self.gtimelog_window.tray_hide.hide()
        # I'm assuming toolkit == 'pygtk' here, since there's now way the old
        # EggTrayIcon can work with PyGI/Gtk+ 3.
        widget.popup(None, None, None, event.button, event.time)

    def on_release(self, widget, event):
        """A mouse button was released on the tray icon label."""
        if event.button != 1:
            return
        self.gtimelog_window.toggle_visible()

    def entry_added(self, entry):
        """An entry has been added."""
        self.tick(force_update=True)

    def tick(self, force_update=False):
        """Tick every second."""
        now = datetime.datetime.now().replace(second=0, microsecond=0)
        if now != self.last_tick or force_update: # Do not eat CPU too much
            self.last_tick = now
            last_time = self.timelog.window.last_time()
            if last_time is None:
                self.time_label.set_text(now.strftime('%H:%M'))
            else:
                self.time_label.set_text(
                    format_duration_short(now - last_time))
        self.trayicon.set_tooltip_text(self.tip())
        return True

    def tip(self):
        """Compute tooltip text."""
        current_task = self.gtimelog_window.task_entry.get_text()
        if not current_task:
            current_task = 'nothing'
        tip = 'GTimeLog: working on {0}'.format(current_task)
        total_work, total_slacking = self.timelog.window.totals()
        tip += '\nWork done today: {0}'.format(format_duration(total_work))
        time_left = self.gtimelog_window.time_left_at_work(total_work)
        if time_left is not None:
            if time_left < datetime.timedelta(0):
                time_left = datetime.timedelta(0)
            tip += '\nTime left at work: {0}'.format(
                format_duration(time_left))
        return tip


class MainWindow:
    """Main application window."""

    # URL to use for Help -> Online Documentation.
    help_url = "http://mg.pov.lt/gtimelog"

    def __init__(self, timelog, settings, tasks):
        """Create the main window."""
        self.timelog = timelog
        self.settings = settings
        self.tasks = tasks
        self.tray_icon = None
        self.last_tick = None
        self.footer_mark = None
        # Try to prevent timer routines mucking with the buffer while we're
        # mucking with the buffer.  Not sure if it is necessary.
        self.lock = False
        # I'm representing a tristate with two booleans (for config file
        # backwards compat), let's normalize nonsensical states.
        self.chronological = (settings.chronological
                              and not settings.summary_view)
        self.summary_view = settings.summary_view
        self.show_tasks = settings.show_tasks
        self.looking_at_date = None
        self.entry_watchers = []
        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        builder = gtk.Builder()
        builder.add_from_file(ui_file)
        # Set initial state of menu items *before* we hook up signals
        chronological_menu_item = builder.get_object('chronological')
        chronological_menu_item.set_active(self.chronological)
        summary_menu_item = builder.get_object('summary')
        summary_menu_item.set_active(self.summary_view)
        show_task_pane_item = builder.get_object('show_task_pane')
        show_task_pane_item.set_active(self.show_tasks)
        # Now hook up signals.
        builder.connect_signals(self)
        # Store references to UI elements we're going to need later
        self.app_indicator_menu = builder.get_object('app_indicator_menu')
        self.appind_show = builder.get_object('appind_show')
        self.tray_icon_popup_menu = builder.get_object('tray_icon_popup_menu')
        self.tray_show = builder.get_object('tray_show')
        self.tray_hide = builder.get_object('tray_hide')
        self.tray_show.hide()
        self.about_dialog = builder.get_object('about_dialog')
        self.about_dialog_ok_btn = builder.get_object('ok_button')
        self.about_dialog_ok_btn.connect('clicked', self.close_about_dialog)
        self.about_text = builder.get_object('about_text')
        self.about_text.set_markup(
            self.about_text.get_label() % dict(version=__version__))
        self.calendar_dialog = builder.get_object('calendar_dialog')
        self.calendar = builder.get_object('calendar')
        self.calendar.connect(
            'day_selected_double_click',
            self.on_calendar_day_selected_double_click)
        self.two_calendar_dialog = builder.get_object('two_calendar_dialog')
        self.calendar1 = builder.get_object('calendar1')
        self.calendar2 = builder.get_object('calendar2')
        self.main_window = builder.get_object('main_window')
        self.main_window.connect('delete_event', self.delete_event)
        self.current_view_label = builder.get_object('current_view_label')
        self.log_view = builder.get_object('log_view')
        self.set_up_log_view_columns()
        self.task_pane = builder.get_object('task_list_pane')
        if not self.show_tasks:
            self.task_pane.hide()
        self.task_pane_info_label = builder.get_object('task_pane_info_label')
        self.tasks.loading_callback = self.task_list_loading
        self.tasks.loaded_callback = self.task_list_loaded
        self.tasks.error_callback = self.task_list_error
        self.task_list = builder.get_object('task_list')
        self.task_store = gtk.TreeStore(str, str)
        self.task_list.set_model(self.task_store)
        column = gtk.TreeViewColumn('Task', gtk.CellRendererText(), text=0)
        self.task_list.append_column(column)
        self.task_list.connect('row_activated', self.task_list_row_activated)
        self.task_list_popup_menu = builder.get_object('task_list_popup_menu')
        self.task_list.connect_object(
            'button_press_event',
            self.task_list_button_press,
            self.task_list_popup_menu)
        task_list_edit_menu_item = builder.get_object('task_list_edit')
        if not self.settings.edit_task_list_cmd:
            task_list_edit_menu_item.set_sensitive(False)
        self.time_label = builder.get_object('time_label')
        self.task_entry = builder.get_object('task_entry')
        self.task_entry.connect('changed', self.task_entry_changed)
        self.task_entry.connect('key_press_event', self.task_entry_key_press)
        self.add_button = builder.get_object('add_button')
        self.add_button.connect('clicked', self.add_entry)
        buffer = self.log_view.get_buffer()
        self.log_buffer = buffer
        buffer.create_tag('today', foreground='blue')
        buffer.create_tag('duration', foreground='red')
        buffer.create_tag('time', foreground='green')
        buffer.create_tag('slacking', foreground='gray')
        self.set_up_task_list()
        self.set_up_completion()
        self.set_up_history()
        self.populate_log()
        self.update_show_checkbox()
        self.tick(True)
        gobject.timeout_add_seconds(1, self.tick)

    def set_up_log_view_columns(self):
        """Set up tab stops in the log view."""
        # we can't get a Pango context for unrealized widgets
        self.log_view.realize()
        pango_context = self.log_view.get_pango_context()
        em = pango_context.get_font_description().get_size()
        tabs = pango_tabarray_new(2, False)
        tabs.set_tab(0, PANGO_ALIGN_LEFT, 9 * em)
        tabs.set_tab(1, PANGO_ALIGN_LEFT, 12 * em)
        self.log_view.set_tabs(tabs)

    def w(self, text, tag=None):
        """Write some text at the end of the log buffer."""
        buffer = self.log_buffer
        if tag:
            buffer.insert_with_tags_by_name(buffer.get_end_iter(), text, tag)
        else:
            buffer.insert(buffer.get_end_iter(), text)

    def populate_log(self):
        """Populate the log."""
        self.lock = True
        buffer = self.log_buffer
        buffer.set_text('')
        if self.footer_mark is not None:
            buffer.delete_mark(self.footer_mark)
            self.footer_mark = None
        if self.looking_at_date is None:
            today = self.timelog.day
            window = self.timelog.window
        else:
            today = self.looking_at_date
            window = self.timelog.window_for_day(today)
        today = "{:%A, %Y-%m-%d} (week {:0>2})".format(today,
                                                       today.isocalendar()[1])
        self.current_view_label.set_text(today)
        if self.chronological:
            for item in window.all_entries():
                self.write_item(item)
        elif self.summary_view:
            entries, totals = window.categorized_work_entries()
            no_cat = totals.pop(None, None)
            if no_cat is not None:
                self.write_group('no category', no_cat)
            for category, duration in sorted(totals.items()):
                self.write_group(category, duration)
            where = buffer.get_end_iter()
            where.backward_cursor_position()
            buffer.place_cursor(where)
        else:
            work, slack = window.grouped_entries()
            for start, entry, duration in work + slack:
                self.write_group(entry, duration)
            where = buffer.get_end_iter()
            where.backward_cursor_position()
            buffer.place_cursor(where)
        self.add_footer()
        self.scroll_to_end()
        self.lock = False

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
        window = self.daily_window(self.looking_at_date)
        total_work, total_slacking = window.totals()
        weekly_window = self.weekly_window(self.looking_at_date)
        week_total_work, week_total_slacking = weekly_window.totals()
        work_days_this_week = weekly_window.count_days()

        self.w('\n')
        self.w('Total work done: ')
        self.w(format_duration(total_work), 'duration')
        self.w(' (')
        self.w(format_duration(week_total_work), 'duration')
        self.w(' this week')
        if work_days_this_week:
            per_diem = week_total_work / work_days_this_week
            self.w(', ')
            self.w(format_duration(per_diem), 'duration')
            self.w(' per day')
        self.w(')\n')
        self.w('Total slacking: ')
        self.w(format_duration(total_slacking), 'duration')
        self.w(' (')
        self.w(format_duration(week_total_slacking), 'duration')
        self.w(' this week')
        if work_days_this_week:
            per_diem = week_total_slacking / work_days_this_week
            self.w(', ')
            self.w(format_duration(per_diem), 'duration')
            self.w(' per day')
        self.w(')\n')

        if self.looking_at_date is None:
            time_left = self.time_left_at_work(total_work)
        else:
            time_left = None
        if time_left is not None:
            time_to_leave = datetime.datetime.now() + time_left
            if time_left < datetime.timedelta(0):
                time_left = datetime.timedelta(0)
            self.w('Time left at work: ')
            self.w(format_duration(time_left), 'duration')
            self.w(' (till ')
            self.w(time_to_leave.strftime('%H:%M'), 'time')
            self.w(')')

        if self.settings.show_office_hours and self.looking_at_date is None:
            self.w('\nAt office today: ')
            hours = datetime.timedelta(hours=self.settings.hours)
            total = total_slacking + total_work
            self.w("%s " % format_duration(total), 'duration')
            self.w('(')
            if total > hours:
                self.w(format_duration(total - hours), 'duration')
                self.w(' overtime')
            else:
                self.w(format_duration(hours - total), 'duration')
                self.w(' left')
            self.w(')')

    def time_left_at_work(self, total_work):
        """Calculate time left to work."""
        last_time = self.timelog.window.last_time()
        if last_time is None:
            return None
        now = datetime.datetime.now()
        # NB: works with UTF-8-encoded binary strings on Python 2.  This
        # seems harmless for now.
        current_task = self.task_entry.get_text()
        current_task_time = now - last_time
        if '**' in current_task:
            total_time = total_work
        else:
            total_time = total_work + current_task_time
        return datetime.timedelta(hours=self.settings.hours) - total_time

    def write_item(self, item):
        buffer = self.log_buffer
        start, stop, duration, entry = item
        self.w(format_duration(duration), 'duration')
        period = '\t({0}-{1})\t'.format(
            start.strftime('%H:%M'), stop.strftime('%H:%M'))
        self.w(period, 'time')
        tag = ('slacking' if '**' in entry else None)
        self.w(entry + '\n', tag)
        where = buffer.get_end_iter()
        where.backward_cursor_position()
        buffer.place_cursor(where)

    def write_group(self, entry, duration):
        self.w(format_duration(duration), 'duration')
        tag = ('slacking' if '**' in entry else None)
        self.w('\t' + entry + '\n', tag)

    def scroll_to_end(self):
        buffer = self.log_view.get_buffer()
        end_mark = buffer.create_mark('end', buffer.get_end_iter())
        self.log_view.scroll_to_mark(end_mark, 0, False, 0, 0)
        buffer.delete_mark(end_mark)

    def set_up_task_list(self):
        """Set up the task list pane."""
        self.task_store.clear()
        for group_name, group_items in self.tasks.groups:
            t = self.task_store.append(None, [group_name, group_name + ': '])
            for item in group_items:
                if group_name == self.tasks.other_title:
                    task = item
                else:
                    task = group_name + ': ' + item
                self.task_store.append(t, [item, task])
        self.task_list.expand_all()

    def set_up_history(self):
        """Set up history."""
        self.history = self.timelog.history
        self.filtered_history = []
        self.history_pos = 0
        self.history_undo = ''
        if not self.have_completion:
            return
        self.completion_choices_as_set.clear()
        self.completion_choices.clear()
        for entry in self.history:
            if entry not in self.completion_choices_as_set:
                self.completion_choices.append([entry])
                self.completion_choices_as_set.add(entry)

    def set_up_completion(self):
        """Set up autocompletion."""
        if not self.settings.enable_gtk_completion:
            self.have_completion = False
            return
        self.have_completion = hasattr(gtk, 'EntryCompletion')
        if not self.have_completion:
            return
        self.completion_choices = gtk.ListStore(str)
        self.completion_choices_as_set = set()
        completion = gtk.EntryCompletion()
        completion.set_model(self.completion_choices)
        completion.set_text_column(0)
        self.task_entry.set_completion(completion)

    def add_history(self, entry):
        """Add an entry to history."""
        self.history.append(entry)
        self.history_pos = 0
        if not self.have_completion:
            return
        if entry not in self.completion_choices_as_set:
            self.completion_choices.append([entry])
            self.completion_choices_as_set.add(entry)

    def jump_to_date(self, date):
        """Switch to looking at a given date"""
        if self.looking_at_date == date:
            return
        self.looking_at_date = date
        self.populate_log()

    def jump_to_today(self):
        """Switch to looking at today"""
        self.jump_to_date(None)

    def delete_event(self, widget, data=None):
        """Try to close the window."""
        if self.tray_icon:
            self.on_hide_activate()
            return True
        else:
            gtk.main_quit()
            return False

    def close_about_dialog(self, widget):
        """Ok clicked in the about dialog."""
        self.about_dialog.hide()

    def on_show_activate(self, widget=None):
        """Tray icon menu -> Show selected"""
        self.main_window.present()
        self.tray_show.hide()
        self.tray_hide.show()
        self.update_show_checkbox()

    def on_hide_activate(self, widget=None):
        """Tray icon menu -> Hide selected"""
        self.main_window.hide()
        self.tray_hide.hide()
        self.tray_show.show()
        self.update_show_checkbox()

    def update_show_checkbox(self):
        self.ignore_on_toggle_visible = True
        # This next line triggers both 'activate' and 'toggled' signals.
        self.appind_show.set_active(self.main_window.get_property('visible'))
        self.ignore_on_toggle_visible = False

    ignore_on_toggle_visible = False

    def on_toggle_visible(self, widget=None):
        """Application indicator menu -> Show GTimeLog"""
        if not self.ignore_on_toggle_visible:
            self.toggle_visible()

    def toggle_visible(self):
        """Toggle main window visibility."""
        if self.main_window.get_property('visible'):
            self.on_hide_activate()
        else:
            self.on_show_activate()

    def on_today_toolbutton_clicked(self, widget=None):
        """Toolbar: Back"""
        self.jump_to_today()

    def on_back_toolbutton_clicked(self, widget=None):
        """Toolbar: Back"""
        day = (self.looking_at_date or self.timelog.day)
        self.jump_to_date(day - datetime.timedelta(1))

    def on_forward_toolbutton_clicked(self, widget=None):
        """Toolbar: Forward"""
        day = (self.looking_at_date or self.timelog.day)
        day += datetime.timedelta(1)
        if day >= self.timelog.virtual_today():
            self.jump_to_today()
        else:
            self.jump_to_date(day)

    def on_quit_activate(self, widget):
        """File -> Quit selected"""
        gtk.main_quit()

    def on_about_activate(self, widget):
        """Help -> About selected"""
        self.about_dialog.show()

    def on_online_help_activate(self, widget):
        """Help -> Online Documentation selected"""
        import webbrowser
        webbrowser.open(self.help_url)

    def on_chronological_activate(self, widget):
        """View -> Chronological"""
        self.chronological = True
        self.summary_view = False
        self.populate_log()

    def on_grouped_activate(self, widget):
        """View -> Grouped"""
        self.chronological = False
        self.summary_view = False
        self.populate_log()

    def on_summary_activate(self, widget):
        """View -> Summary"""
        self.chronological = False
        self.summary_view = True
        self.populate_log()

    def daily_window(self, day=None):
        if not day:
            day = self.timelog.day
        return self.timelog.window_for_day(day)

    def on_daily_report_activate(self, widget):
        """File -> Daily Report"""
        reports = Reports(self.timelog.window)
        self.mail(reports.daily_report)

    def on_yesterdays_report_activate(self, widget):
        """File -> Daily Report for Yesterday"""
        day = self.timelog.day - datetime.timedelta(1)
        reports = Reports(self.timelog.window_for_day(day))
        self.mail(reports.daily_report)

    def on_previous_day_report_activate(self, widget):
        """File -> Daily Report for a Previous Day"""
        day = self.choose_date()
        if day:
            reports = Reports(self.timelog.window_for_day(day))
            self.mail(reports.daily_report)

    def choose_date(self):
        """Pop up a calendar dialog.

        Returns either a datetime.date, or None.
        """
        if self.calendar_dialog.run() == GTK_RESPONSE_OK:
            y, m1, d = self.calendar.get_date()
            day = datetime.date(y, m1 + 1, d)
        else:
            day = None
        self.calendar_dialog.hide()
        return day

    def choose_date_range(self):
        """Pop up a calendar dialog for a date range.

        Returns either a tuple with two datetime.date objects, or (None, None).
        """
        if self.two_calendar_dialog.run() == GTK_RESPONSE_OK:
            y1, m1, d1 = self.calendar1.get_date()
            y2, m2, d2 = self.calendar2.get_date()
            first = datetime.date(y1, m1 + 1, d1)
            second = datetime.date(y2, m2 + 1, d2)
        else:
            first = second = None
        self.two_calendar_dialog.hide()
        return (first, second)

    def on_calendar_day_selected_double_click(self, widget):
        """Double-click on a calendar day: close the dialog."""
        self.calendar_dialog.response(GTK_RESPONSE_OK)

    def weekly_window(self, day=None):
        if not day:
            day = self.timelog.day
        return self.timelog.window_for_week(day)

    def on_weekly_report_activate(self, widget):
        """File -> Weekly Report"""
        day = self.timelog.day
        reports = Reports(self.weekly_window(day=day))
        if self.settings.report_style == 'plain':
            report = reports.weekly_report_plain
        elif self.settings.report_style == 'categorized':
            report = reports.weekly_report_categorized
        else:
            report = reports.weekly_report_plain
        self.mail(report)

    def on_last_weeks_report_activate(self, widget):
        """File -> Weekly Report for Last Week"""
        day = self.timelog.day - datetime.timedelta(7)
        reports = Reports(self.weekly_window(day=day))
        if self.settings.report_style == 'plain':
            report = reports.weekly_report_plain
        elif self.settings.report_style == 'categorized':
            report = reports.weekly_report_categorized
        else:
            report = reports.weekly_report_plain
        self.mail(report)

    def on_previous_week_report_activate(self, widget):
        """File -> Weekly Report for a Previous Week"""
        day = self.choose_date()
        if day:
            reports = Reports(self.weekly_window(day=day))
            if self.settings.report_style == 'plain':
                report = reports.weekly_report_plain
            elif self.settings.report_style == 'categorized':
                report = reports.weekly_report_categorized
            else:
                report = reports.weekly_report_plain
            self.mail(report)

    def monthly_window(self, day=None):
        if not day:
            day = self.timelog.day
        return self.timelog.window_for_month(day)

    def on_previous_month_report_activate(self, widget):
        """File -> Monthly Report for a Previous Month"""
        day = self.choose_date()
        if day:
            reports = Reports(self.monthly_window(day=day))
            if self.settings.report_style == 'plain':
                report = reports.monthly_report_plain
            elif self.settings.report_style == 'categorized':
                report = reports.monthly_report_categorized
            else:
                report = reports.monthly_report_plain
            self.mail(report)

    def on_last_month_report_activate(self, widget):
        """File -> Monthly Report for Last Month"""
        day = self.timelog.day - datetime.timedelta(self.timelog.day.day)
        reports = Reports(self.monthly_window(day=day))
        if self.settings.report_style == 'plain':
            report = reports.monthly_report_plain
        elif self.settings.report_style == 'categorized':
            report = reports.monthly_report_categorized
        else:
            report = reports.monthly_report_plain
        self.mail(report)

    def on_monthly_report_activate(self, widget):
        """File -> Monthly Report"""
        reports = Reports(self.monthly_window())
        if self.settings.report_style == 'plain':
            report = reports.monthly_report_plain
        elif self.settings.report_style == 'categorized':
            report = reports.monthly_report_categorized
        else:
            report = reports.monthly_report_plain
        self.mail(report)

    def range_window(self, min, max):
        if not min:
            min = self.timelog.day
        if not max:
            max = self.timelog.day
        if max < min:
            max = min
        return self.timelog.window_for_date_range(min, max)

    def on_custom_range_report_activate(self, widget):
        """File -> Report for a Custom Date Range"""
        min, max = self.choose_date_range()
        if min and max:
            reports = Reports(self.range_window(min, max))
            self.mail(reports.custom_range_report_categorized)

    def on_open_complete_spreadsheet_activate(self, widget):
        """Report -> Complete Report in Spreadsheet"""
        tempfn = tempfile.mktemp(suffix='gtimelog.csv') # XXX unsafe!
        with open(tempfn, 'w') as f:
            self.timelog.whole_history().to_csv_complete(f)
        self.spawn(self.settings.spreadsheet, tempfn)

    def on_open_slack_spreadsheet_activate(self, widget):
        """Report -> Work/_Slacking stats in Spreadsheet"""
        tempfn = tempfile.mktemp(suffix='gtimelog.csv') # XXX unsafe!
        with open(tempfn, 'w') as f:
            self.timelog.whole_history().to_csv_daily(f)
        self.spawn(self.settings.spreadsheet, tempfn)

    def on_edit_timelog_activate(self, widget):
        """File -> Edit timelog.txt"""
        self.spawn(self.settings.editor, '"%s"' % self.timelog.filename)

    def mail(self, write_draft):
        """Send an email."""
        draftfn = tempfile.mktemp(suffix='gtimelog') # XXX unsafe!
        with codecs.open(draftfn, 'w', encoding='UTF-8') as draft:
            write_draft(draft, self.settings.email, self.settings.name)
        self.spawn(self.settings.mailer, draftfn)
        # XXX rm draftfn when done -- but how?

    def spawn(self, command, arg=None):
        """Spawn a process in background"""
        # XXX shell-escape arg, please.
        if arg is not None:
            if '%s' in command:
                command = command % arg
            else:
                command += ' ' + arg
        os.system(command + " &")

    def on_reread_activate(self, widget):
        """File -> Reread"""
        self.timelog.reread()
        self.set_up_history()
        self.populate_log()
        self.tick(True)

    def on_show_task_pane_toggled(self, event):
        """View -> Tasks"""
        if self.task_pane.get_property('visible'):
            self.task_pane.hide()
        else:
            self.task_pane.show()
            if self.tasks.check_reload():
                self.set_up_task_list()

    def on_task_pane_close_button_activate(self, event, data=None):
        """The close button next to the task pane title"""
        self.task_pane.hide()

    def task_list_row_activated(self, treeview, path, view_column):
        """A task was selected in the task pane -- put it to the entry."""
        model = treeview.get_model()
        task = model[path][1]
        self.task_entry.set_text(task)
        def grab_focus():
            self.task_entry.grab_focus()
            self.task_entry.set_position(-1)
        # There's a race here: sometimes the GDK_2BUTTON_PRESS signal is
        # handled _after_ row-activated, which makes the tree control steal
        # the focus back from the task entry.  To avoid this, wait until all
        # the events have been handled.
        gobject.idle_add(grab_focus)

    def task_list_button_press(self, menu, event):
        if event.button == 3:
            if toolkit == "gi":
                menu.popup(None, None, None, None, event.button, event.time)
            else:
                menu.popup(None, None, None, event.button, event.time)
            return True
        else:
            return False

    def on_task_list_reload(self, event):
        self.tasks.reload()
        self.set_up_task_list()

    def on_task_list_edit(self, event):
        self.spawn(self.settings.edit_task_list_cmd)

    def task_list_loading(self):
        self.task_list_loading_failed = False
        self.task_pane_info_label.set_text('Loading...')
        self.task_pane_info_label.show()
        # let the ui update become visible
        while gtk.events_pending():
            gtk.main_iteration()

    def task_list_error(self):
        self.task_list_loading_failed = True
        self.task_pane_info_label.set_text('Could not get task list.')
        self.task_pane_info_label.show()

    def task_list_loaded(self):
        if not self.task_list_loading_failed:
            self.task_pane_info_label.hide()

    def task_entry_changed(self, widget):
        """Reset history position when the task entry is changed."""
        self.history_pos = 0

    def task_entry_key_press(self, widget, event):
        """Handle key presses in task entry."""
        if event.keyval == gdk.keyval_from_name('Escape') and self.tray_icon:
            self.on_hide_activate()
            return True
        if event.keyval == gdk.keyval_from_name('Prior'):
            self._do_history(1)
            return True
        if event.keyval == gdk.keyval_from_name('Next'):
            self._do_history(-1)
            return True
        # XXX This interferes with the completion box.  How do I determine
        # whether the completion box is visible or not?
        if self.have_completion:
            return False
        if event.keyval == gdk.keyval_from_name('Up'):
            self._do_history(1)
            return True
        if event.keyval == gdk.keyval_from_name('Down'):
            self._do_history(-1)
            return True
        return False

    def _get_entry_text(self):
        """Return the current task entry text (as Unicode)."""
        entry = self.task_entry.get_text()
        if not isinstance(entry, unicode):
            entry = unicode(entry, 'UTF-8')
        return entry

    def _do_history(self, delta):
        """Handle movement in history."""
        if not self.history:
            return
        if self.history_pos == 0:
            self.history_undo = self._get_entry_text()
            self.filtered_history = uniq([
                l for l in self.history if l.startswith(self.history_undo)])
        history = self.filtered_history
        new_pos = max(0, min(self.history_pos + delta, len(history)))
        if new_pos == 0:
            self.task_entry.set_text(self.history_undo)
            self.task_entry.set_position(-1)
        else:
            self.task_entry.set_text(history[-new_pos])
            self.task_entry.select_region(0, -1)
        # Do this after task_entry_changed reset history_pos to 0
        self.history_pos = new_pos

    def add_entry(self, widget, data=None):
        """Add the task entry to the log."""
        if self.looking_at_date is not None:
            self.jump_to_today()

        entry = self._get_entry_text()

        now = None
        date_match = re.match(r'(\d\d):(\d\d)\s+', entry)
        delta_match = re.match(r'-([1-9]\d?|1\d\d)\s+', entry)
        if date_match:
            h = int(date_match.group(1))
            m = int(date_match.group(2))
            if 0 <= h < 24 and 0 <= m <= 60:
                now = datetime.datetime.now()
                now = now.replace(hour=h, minute=m, second=0, microsecond=0)
                if self.timelog.valid_time(now):
                    entry = entry[date_match.end():]
                else:
                    now = None
        if delta_match:
            seconds = int(delta_match.group()) * 60
            now = datetime.datetime.now().replace(second=0, microsecond=0)
            now += datetime.timedelta(seconds=seconds)
            if self.timelog.valid_time(now):
                entry = entry[delta_match.end():]
            else:
                now = None

        if not entry:
            return
        self.add_history(entry)
        previous_day = self.timelog.day
        self.timelog.append(entry, now)
        same_day = self.timelog.day == previous_day
        if self.chronological and same_day:
            self.delete_footer()
            self.write_item(self.timelog.window.last_entry())
            self.add_footer()
            self.scroll_to_end()
        else:
            self.populate_log()
        self.task_entry.set_text('')
        self.task_entry.grab_focus()
        self.tick(True)
        for watcher in self.entry_watchers:
            watcher(entry)

    def tick(self, force_update=False):
        """Tick every second."""
        if self.timelog.check_reload():
            self.populate_log()
            self.set_up_history()
            force_update = True
        if self.task_pane.get_property('visible'):
            if self.tasks.check_reload():
                self.set_up_task_list()
        now = datetime.datetime.now().replace(second=0, microsecond=0)
        if now == self.last_tick and not force_update:
            # Do not eat CPU unnecessarily: update the time ticker only when
            # the minute changes.
            return True
        self.last_tick = now
        last_time = self.timelog.window.last_time()
        if last_time is None:
            self.time_label.set_text(now.strftime('%H:%M'))
        else:
            self.time_label.set_text(format_duration(now - last_time))
            # Update "time left to work"
            if not self.lock and self.looking_at_date is None:
                self.delete_footer()
                self.add_footer()
        return True


if dbus:
    INTERFACE = 'lt.pov.mg.gtimelog.Service'
    OBJECT_PATH = '/lt/pov/mg/gtimelog/Service'
    SERVICE = 'lt.pov.mg.gtimelog.GTimeLog'

    class Service(dbus.service.Object):
        """Our DBus service, used to communicate with the main instance."""

        def __init__(self, main_window):
            session_bus = dbus.SessionBus()
            connection = dbus.service.BusName(SERVICE, session_bus)
            dbus.service.Object.__init__(self, connection, OBJECT_PATH)

            self.main_window = main_window

        @dbus.service.method(INTERFACE)
        def ToggleFocus(self):
            self.main_window.toggle_visible()

        @dbus.service.method(INTERFACE)
        def Present(self):
            self.main_window.on_show_activate()

        @dbus.service.method(INTERFACE)
        def Quit(self):
            gtk.main_quit()


def main():
    """Run the program."""
    parser = optparse.OptionParser(usage='%prog [options]',
                                   version=gtimelog.__version__)
    parser.add_option('--tray', action='store_true',
        help="start minimized")
    parser.add_option('--sample-config', action='store_true',
        help="write a sample configuration file to 'gtimelogrc.sample'")

    dbus_options = optparse.OptionGroup(parser, "Single-Instance Options")
    dbus_options.add_option('--replace', action='store_true',
        help="replace the already running GTimeLog instance")
    dbus_options.add_option('--quit', action='store_true',
        help="tell an already-running GTimeLog instance to quit")
    dbus_options.add_option('--toggle', action='store_true',
        help="show/hide the GTimeLog window if already running")
    dbus_options.add_option('--ignore-dbus', action='store_true',
        help="do not check if GTimeLog is already running"
             " (allows you to have multiple instances running)")
    parser.add_option_group(dbus_options)

    debug_options = optparse.OptionGroup(parser, "Debugging Options")
    debug_options.add_option('--debug', action='store_true',
        help="show debug information")
    debug_options.add_option('--prefer-pygtk', action='store_true',
        help="try to use the (obsolete) pygtk library instead of pygi")
    parser.add_option_group(debug_options)

    opts, args = parser.parse_args()

    log.addHandler(logging.StreamHandler(sys.stdout))
    if opts.debug:
        log.setLevel(logging.DEBUG)
    else:
        log.setLevel(logging.INFO)

    if opts.sample_config:
        settings = Settings()
        settings.save("gtimelogrc.sample")
        print("Sample configuration file written to gtimelogrc.sample")
        print("Edit it and save as %s" % settings.get_config_file())
        return

    global dbus

    if opts.debug:
        print('GTimeLog version: %s' % gtimelog.__version__)
        print('Python version: %s' % sys.version)
        print('Toolkit: %s' % toolkit)
        print('Gtk+ version: %s' % gtk_version)
        print('D-Bus available: %s' % ('yes' if dbus else 'no'))
        print('Config directory: %s' % Settings().get_config_dir())
        print('Data directory: %s' % Settings().get_data_dir())

    if opts.ignore_dbus:
        dbus = None

    # Let's check if there is already an instance of GTimeLog running
    # and if it is make it present itself or when it is already presented
    # hide it and then quit.
    if dbus:
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

        try:
            session_bus = dbus.SessionBus()
            dbus_service = session_bus.get_object(SERVICE, OBJECT_PATH)
            if opts.replace or opts.quit:
                print('gtimelog: Telling the already-running instance to quit')
                dbus_service.Quit()
                if opts.quit:
                    sys.exit()
            elif opts.toggle:
                dbus_service.ToggleFocus()
                print('gtimelog: Already running, toggling visibility')
                sys.exit()
            elif opts.tray:
                print('gtimelog: Already running, not doing anything')
                sys.exit()
            else:
                dbus_service.Present()
                print('gtimelog: Already running, presenting main window')
                sys.exit()
        except dbus.DBusException as e:
            if e.get_dbus_name() == 'org.freedesktop.DBus.Error.ServiceUnknown':
                # gtimelog is not running: that's fine and not an error at all
                if opts.quit:
                    print('gtimelog is not running')
                    sys.exit()
            elif opts.quit or opts.replace or opts.toggle:
                # we need dbus to work for this, so abort
                sys.exit('gtimelog: %s' % e)
            else:
                # otherwise just emit a warning
                print("gtimelog: dbus is not available:\n  %s" % e)
    else: # not dbus
        if opts.quit or opts.replace or opts.toggle:
            sys.exit("gtimelog: dbus not available")

    settings = Settings()
    configdir = settings.get_config_dir()
    datadir = settings.get_data_dir()
    try:
        # Create configdir if it doesn't exist.
        os.makedirs(configdir)
    except OSError as error:
        if error.errno != errno.EEXIST:
            # XXX: not the most friendly way of error reporting for a GUI app
            raise
    try:
        # Create datadir if it doesn't exist.
        os.makedirs(datadir)
    except OSError as error:
        if error.errno != errno.EEXIST:
            raise

    settings_file = settings.get_config_file()
    if not os.path.exists(settings_file):
        if opts.debug:
            print('Saving settings to %s' % settings_file)
        settings.save(settings_file)
    else:
        if opts.debug:
            print('Loading settings from %s' % settings_file)
        settings.load(settings_file)
    if opts.debug:
        print('Assuming date changes at %s' % settings.virtual_midnight)
        print('Loading time log from %s' % settings.get_timelog_file())
    timelog = TimeLog(settings.get_timelog_file(),
                      settings.virtual_midnight)
    if settings.task_list_url:
        if opts.debug:
            print('Loading cached remote tasks from %s' %
                  os.path.join(datadir, 'remote-tasks.txt'))
        tasks = RemoteTaskList(settings.task_list_url,
                               os.path.join(datadir, 'remote-tasks.txt'))
    else:
        if opts.debug:
            print('Loading tasks from %s' % os.path.join(datadir, 'tasks.txt'))
        tasks = TaskList(os.path.join(datadir, 'tasks.txt'))
    main_window = MainWindow(timelog, settings, tasks)
    start_in_tray = False
    if settings.show_tray_icon:
        if settings.prefer_app_indicator:
            icons = [AppIndicator, SimpleStatusIcon, OldTrayIcon]
        elif settings.prefer_old_tray_icon:
            icons = [OldTrayIcon, SimpleStatusIcon, AppIndicator]
        else:
            icons = [SimpleStatusIcon, OldTrayIcon, AppIndicator]
        if opts.debug:
            print('Tray icon preference: %s' % ', '.join(icon_class.__name__
                                                         for icon_class in icons))
        for icon_class in icons:
            tray_icon = icon_class(main_window)
            if tray_icon.available():
                if opts.debug:
                    print('Tray icon: %s' % icon_class.__name__)
                start_in_tray = (settings.start_in_tray
                                 if settings.start_in_tray
                                 else opts.tray)
                break # found one that works
            else:
                if opts.debug:
                    print('%s not available' % icon_class.__name__)
    if not start_in_tray:
        main_window.on_show_activate()
    else:
        if opts.debug:
            print('Starting minimized')
    if dbus:
        try:
            service = Service(main_window)  # noqa
        except dbus.DBusException as e:
            print("gtimelog: dbus is not available:\n  %s" % e)
    # This is needed to make ^C terminate gtimelog when we're using
    # gobject-introspection.
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    try:
        gtk.main()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
