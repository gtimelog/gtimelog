"""An application for keeping track of your time."""

# Default to new-style classes.
__metaclass__ = type

import os
import sys
import errno
import codecs
import signal
import logging
import datetime
import tempfile

import gtimelog


log = logging.getLogger('gtimelog')


try:
    unicode
except NameError:
    unicode = str

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GObject, GLib, Gdk, Gio, Gtk, Pango

try:
    from gi.repository import AppIndicator3
    have_app_indicator = True
except ImportError:
    have_app_indicator = False

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
    format_duration, uniq,
    Reports, TimeLog, TaskList, RemoteTaskList)


class IconChooser:
    """Picks the right icon for dark or bright panel backgrounds.

    Well, tries to pick it.  I couldn't find a way to determine the color of
    the panel, so I cheated by assuming it'll be the same as the color of
    the menu bar.  This is wrong for many popular themes, including:

    - Adwaita
    - Radiance
    - Ambiance

    which is why I have to maintain a list of per-theme overrides.
    """

    icon_for_background = dict(
        # We want sufficient contrast, so:
        # - use dark icon for bright backgrounds
        # - use bright icon for dark backgrounds
        bright=icon_file_dark,
        dark=icon_file_bright,
    )

    theme_overrides = {
        # when the menu bar color logic gets this wrong
        'Adwaita': 'dark',  # but probably only under gnome-shell
        'Ambiance': 'dark',
        'Radiance': 'bright',
    }

    @property
    def icon_name(self):
        theme_name = self.get_gtk_theme()
        background = self.get_background()
        if theme_name in self.theme_overrides:
            background = self.theme_overrides[theme_name]
            log.debug('Overriding background to %s for %s', background, theme_name)
        filename = self.icon_for_background[background]
        log.debug('For %s background picking icon %s', background, filename)
        return filename

    def get_gtk_theme(self):
        theme_name = Gtk.Settings.get_default().props.gtk_theme_name
        log.debug('GTK+ theme: %s', theme_name)
        override = os.environ.get('GTK_THEME')
        if override:
            log.debug('GTK_THEME overrides the theme to %s', override)
            theme_name = override.partition(':')[0]
        return theme_name

    def get_background(self):
        menu_bar = Gtk.MenuBar()
        # need to hold a reference to menu_bar to avoid LP#1016212
        style = menu_bar.get_style_context()
        color = style.get_color(Gtk.StateFlags.NORMAL)
        value = (color.red + color.green + color.blue) / 3
        background = 'bright' if value >= 0.5 else 'dark'
        log.debug('Menu bar color: (%.3g, %.3g, %.3g), averages to %.3g (%s)',
                  color.red, color.green, color.blue, value, background)
        return background


class SimpleStatusIcon(IconChooser):
    """Status icon for gtimelog in the notification area."""

    def __init__(self, gtimelog_window):
        self.gtimelog_window = gtimelog_window
        self.timelog = gtimelog_window.timelog
        self.trayicon = None
        self.icon = Gtk.StatusIcon.new_from_file(self.icon_name)
        self.last_tick = False
        self.tick()
        self.icon.connect('activate', self.on_activate)
        self.icon.connect('popup-menu', self.on_popup_menu)
        self.gtimelog_window.main_window.connect(
            'style-updated', self.on_style_set)
        GLib.timeout_add_seconds(1, self.tick)
        self.gtimelog_window.entry_watchers.append(self.entry_added)
        self.gtimelog_window.tray_icon = self

    def on_style_set(self, *args):
        """The user chose a different theme."""
        self.icon.set_from_file(self.icon_name)

    def on_activate(self, widget):
        """The user clicked on the icon."""
        self.gtimelog_window.toggle_visible()

    def on_popup_menu(self, widget, button, activate_time):
        """The user clicked on the icon."""
        tray_icon_popup_menu = self.gtimelog_window.tray_icon_popup_menu
        tray_icon_popup_menu.popup(
            None, None, Gtk.StatusIcon.position_menu,
            self.icon, button, activate_time)

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

    def __init__(self, gtimelog_window):
        self.gtimelog_window = gtimelog_window
        self.timelog = gtimelog_window.timelog
        self.indicator = None
        if have_app_indicator:
            self.indicator = AppIndicator3.Indicator.new(
                'gtimelog', self.icon_name, AppIndicator3.IndicatorCategory.APPLICATION_STATUS)
            self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
            self.indicator.set_menu(gtimelog_window.app_indicator_menu)
            self.gtimelog_window.tray_icon = self
            self.gtimelog_window.main_window.connect(
                'style-updated', self.on_style_set)

    def on_style_set(self, *args):
        """The user chose a different theme."""
        self.indicator.set_icon(self.icon_name)


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
        builder = Gtk.Builder()
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
        self.task_store = Gtk.TreeStore(str, str)
        self.task_list.set_model(self.task_store)
        column = Gtk.TreeViewColumn('Task', Gtk.CellRendererText(), text=0)
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
        buffer.create_tag('today', foreground='#204a87')  # Tango dark blue
        buffer.create_tag('duration', foreground='#ce5c00')  # Tango dark orange
        buffer.create_tag('time', foreground='#4e9a06')  # Tango dark green
        buffer.create_tag('slacking', foreground='gray')
        self.set_up_task_list()
        self.set_up_completion()
        self.set_up_history()
        self.populate_log()
        self.update_show_checkbox()
        self.tick(True)
        GLib.timeout_add_seconds(1, self.tick)

    def quit(self):
        self.main_window.destroy()

    def set_up_log_view_columns(self):
        """Set up tab stops in the log view."""
        # we can't get a Pango context for unrealized widgets
        self.log_view.realize()
        pango_context = self.log_view.get_pango_context()
        em = pango_context.get_font_description().get_size()
        tabs = Pango.TabArray.new(2, False)
        tabs.set_tab(0, Pango.TabAlign.LEFT, 9 * em)
        tabs.set_tab(1, Pango.TabAlign.LEFT, 12 * em)
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
        start, stop, duration, tags, entry = item
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
        self.have_completion = hasattr(Gtk, 'EntryCompletion')
        if not self.have_completion:
            return
        self.completion_choices = Gtk.ListStore(str)
        self.completion_choices_as_set = set()
        completion = Gtk.EntryCompletion()
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
            self.quit()
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
        self.quit()

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
        if self.calendar_dialog.run() == Gtk.ResponseType.OK:
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
        if self.two_calendar_dialog.run() == Gtk.ResponseType.OK:
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
        self.calendar_dialog.response(Gtk.ResponseType.OK)

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
        tempfn = tempfile.mktemp(prefix='gtimelog-', suffix='.csv') # XXX unsafe!
        with open(tempfn, 'w') as f:
            self.timelog.whole_history().to_csv_complete(f)
        self.spawn(self.settings.spreadsheet, tempfn)

    def on_open_slack_spreadsheet_activate(self, widget):
        """Report -> Work/_Slacking stats in Spreadsheet"""
        tempfn = tempfile.mktemp(prefix='gtimelog-', suffix='.csv') # XXX unsafe!
        with open(tempfn, 'w') as f:
            self.timelog.whole_history().to_csv_daily(f)
        self.spawn(self.settings.spreadsheet, tempfn)

    def on_edit_timelog_activate(self, widget):
        """File -> Edit timelog.txt"""
        self.spawn(self.settings.editor, '"%s"' % self.timelog.filename)

    def mail(self, write_draft):
        """Send an email."""
        draftfn = tempfile.mktemp(prefix='gtimelog-') # XXX unsafe!
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
        GObject.idle_add(grab_focus)

    def task_list_button_press(self, menu, event):
        if event.button == 3:
            menu.popup(None, None, None, None, event.button, event.time)
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
        while Gtk.events_pending():
            Gtk.main_iteration()

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
        if event.keyval == Gdk.keyval_from_name('Escape') and self.tray_icon:
            self.on_hide_activate()
            return True
        if event.keyval == Gdk.keyval_from_name('Prior'):
            self._do_history(1)
            return True
        if event.keyval == Gdk.keyval_from_name('Next'):
            self._do_history(-1)
            return True
        # XXX This interferes with the completion box.  How do I determine
        # whether the completion box is visible or not?
        if self.have_completion:
            return False
        if event.keyval == Gdk.keyval_from_name('Up'):
            self._do_history(1)
            return True
        if event.keyval == Gdk.keyval_from_name('Down'):
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
        entry, now = self.timelog.parse_correction(entry)
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


def make_option(long_name, short_name=None, flags=0, arg=GLib.OptionArg.NONE,
                arg_data=None, description=None, arg_description=None):
    # surely something like this should exist inside PyGObject itself?!
    option = GLib.OptionEntry()
    option.long_name = long_name.lstrip('-')
    option.short_name = 0 if not short_name else short_name.lstrip('-')
    option.flags = flags
    option.arg = arg
    option.arg_data = arg_data
    option.description = description
    option.arg_description = arg_description
    return option


class Application(Gtk.Application):
    def __init__(self, *args, **kwargs):
        kwargs['application_id'] = 'lt.pov.mg.gtimelog'
        kwargs['flags'] = Gio.ApplicationFlags.HANDLES_COMMAND_LINE
        Gtk.Application.__init__(self, *args, **kwargs)
        self.add_main_option_entries([
            make_option("--version", description="Show version number and exit"),
            make_option("--tray", description="Start minimized"),
            make_option("--toggle", description="Show/hide the GTimeLog window if already running"),
            make_option("--quit", description="Tell an already-running GTimeLog instance to quit"),
            make_option("--sample-config", description="Write a sample configuration file to 'gtimelogrc.sample'"),
            make_option("--debug", description="Show debug information"),
        ])
        self.main_window = None
        self.debug = False
        self.start_minimized = False

    def do_handle_local_options(self, options):
        if options.contains('version'):
            print(gtimelog.__version__)
            return 0
        if options.contains('sample-config'):
            settings = Settings()
            settings.save("gtimelogrc.sample")
            print("Sample configuration file written to gtimelogrc.sample")
            print("Edit it and save as %s" % settings.get_config_file())
            return 0
        self.debug = options.contains('debug')
        self.start_minimized = options.contains('tray')
        if options.contains('quit'):
            print('gtimelog: Telling the already-running instance to quit')
        return -1  # send the args to the remote instance for processing

    def do_command_line(self, command_line):
        options = command_line.get_options_dict()
        if options.contains('toggle') and self.main_window is not None:
            # NB: Even if there's no tray icon, it's still possible to
            # hide the gtimelog window.  Bug or feature?
            self.main_window.toggle_visible()
            return 0
        if options.contains('quit'):
            if self.main_window:
                self.main_window.quit()
            else:
                print('gtimelog: not running')
            return 0

        self.do_activate()
        return 0

    def do_activate(self):
        if self.main_window is not None:
            self.main_window.main_window.present()
            return

        debug = self.debug
        start_minimized = self.start_minimized

        log.addHandler(logging.StreamHandler(sys.stdout))
        if debug:
            log.setLevel(logging.DEBUG)
        else:
            log.setLevel(logging.INFO)

        if debug:
            print('GTimeLog version: %s' % gtimelog.__version__)
            print('Python version: %s' % sys.version)
            print('Gtk+ version: %s.%s.%s' % (Gtk.MAJOR_VERSION, Gtk.MINOR_VERSION, Gtk.MICRO_VERSION))
            print('Config directory: %s' % Settings().get_config_dir())
            print('Data directory: %s' % Settings().get_data_dir())

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
            if debug:
                print('Saving settings to %s' % settings_file)
            settings.save(settings_file)
        else:
            if debug:
                print('Loading settings from %s' % settings_file)
            settings.load(settings_file)
        if debug:
            print('Assuming date changes at %s' % settings.virtual_midnight)
            print('Loading time log from %s' % settings.get_timelog_file())
        timelog = TimeLog(settings.get_timelog_file(),
                          settings.virtual_midnight)
        if settings.task_list_url:
            if debug:
                print('Loading cached remote tasks from %s' %
                      os.path.join(datadir, 'remote-tasks.txt'))
            tasks = RemoteTaskList(settings.task_list_url,
                                   os.path.join(datadir, 'remote-tasks.txt'))
        else:
            if debug:
                print('Loading tasks from %s' % os.path.join(datadir, 'tasks.txt'))
            tasks = TaskList(os.path.join(datadir, 'tasks.txt'))
        self.main_window = MainWindow(timelog, settings, tasks)
        self.add_window(self.main_window.main_window)
        start_in_tray = False

        if settings.show_tray_icon:
            if debug:
                print('Tray icon preference: %s' % ('AppIndicator'
                                                    if settings.prefer_app_indicator
                                                    else 'SimpleStatusIcon'))

            if settings.prefer_app_indicator and have_app_indicator:
                tray_icon = AppIndicator(self.main_window)
            else:
                tray_icon = SimpleStatusIcon(self.main_window)

            if tray_icon:
                if debug:
                    print('Using: %s' % tray_icon.__class__.__name__)

                start_in_tray = (settings.start_in_tray
                                 if settings.start_in_tray
                                 else start_minimized)

        if debug:
            print('GTK+ completion: %s' % ('enabled' if settings.enable_gtk_completion else 'disabled'))

        if not start_in_tray:
            self.main_window.on_show_activate()
        else:
            if debug:
                print('Starting minimized')

        # This is needed to make ^C terminate gtimelog when we're using
        # gobject-introspection.
        signal.signal(signal.SIGINT, signal.SIG_DFL)


def main():
    """Run the program."""
    app = Application()
    app.run(sys.argv)

if __name__ == '__main__':
    main()
