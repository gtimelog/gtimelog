#!/usr/bin/python
from __future__ import print_function

import datetime
import gettext
import locale
import os
import signal
import sys
from gettext import gettext as _

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, Gio, GLib, GObject

pkgdir = os.path.join(os.path.dirname(__file__), 'src')
sys.path.insert(0, pkgdir)

from gtimelog.settings import Settings


HELP_URL = 'https://mg.pov.lt/gtimelog'

UI_FILE = 'src/gtimelog/experiment.ui'
ABOUT_DIALOG_UI_FILE = 'src/gtimelog/about.ui'
MENUS_UI_FILE = 'src/gtimelog/menus.ui'
LOCALE_DIR = 'locale'


class Application(Gtk.Application):

    def __init__(self):
        super(Application, self).__init__(application_id='lt.pov.mg.gtimelog_mockup')
        GLib.set_application_name(_("Time Log"))
        GLib.set_prgname('gtimelog')

    def do_startup(self):
        Gtk.Application.do_startup(self)

        builder = Gtk.Builder.new_from_file(MENUS_UI_FILE)
        self.set_app_menu(builder.get_object('app_menu'))

        for action_name in ['help', 'about', 'quit', 'edit-log']:
            action = Gio.SimpleAction.new(action_name, None)
            action.connect('activate', getattr(self, 'on_' + action_name.replace('-', '_')))
            self.add_action(action)

        self.set_accels_for_action("win.detail-level('chronological')", ["<Alt>1"])
        self.set_accels_for_action("win.detail-level('grouped')", ["<Alt>2"])
        self.set_accels_for_action("win.detail-level('summary')", ["<Alt>3"])
        self.set_accels_for_action("win.show-task-pane", ["F9"])
        self.set_accels_for_action("win.go-back", ["<Alt>Left"])
        self.set_accels_for_action("win.go-forward", ["<Alt>Right"])
        self.set_accels_for_action("win.go-home", ["<Alt>Home"])
        self.set_accels_for_action("app.edit-log", ["<Primary>E"])
        self.set_accels_for_action("app.quit", ["<Primary>Q"])
        self.set_accels_for_action("win.send-report", ["<Primary>D"])

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
        if self.get_active_window() is not None:
            self.get_active_window().present()
            return

        window = Window(self)
        self.add_window(window)
        window.show()


class Window(Gtk.ApplicationWindow):

    date = GObject.Property(
        type=object, default=None, nick='Date',
        blurb='Currently visible date')

    class Actions(object):

        def __init__(self, win, builder):
            self.detail_level = Gio.SimpleAction.new_stateful("detail-level", GLib.VariantType.new("s"), GLib.Variant("s", "chronological"))
            win.add_action(self.detail_level)

            self.time_range = Gio.SimpleAction.new_stateful("time-range", GLib.VariantType.new("s"), GLib.Variant("s", "day"))
            win.add_action(self.time_range)

            self.show_task_pane = Gio.PropertyAction.new("show-task-pane", builder.get_object("task_pane"), "visible")
            win.add_action(self.show_task_pane)

            for action_name in ['go-back', 'go-forward', 'go-home']:
                action = Gio.SimpleAction.new(action_name, None)
                action.connect('activate', getattr(win, 'on_' + action_name.replace('-', '_')))
                win.add_action(action)
                setattr(self, action_name.replace('-', '_'), action)

    def __init__(self, app):
        Gtk.ApplicationWindow.__init__(self, application=app, icon_name='gtimelog')

        builder = Gtk.Builder.new_from_file(UI_FILE)
        builder.add_from_file(MENUS_UI_FILE)
        main_window = builder.get_object('main_window')
        main_box = builder.get_object('main_box')
        headerbar = builder.get_object('headerbar')
        main_window.set_titlebar(None)
        main_window.remove(main_box)
        self.add(main_box)
        self.set_titlebar(headerbar)
        self.set_default_size(800, 500)

        # Cannot store these in the same .ui file nor hook them up in the
        # .ui because glade doesn't support that and strips both the
        # <menu> and the menu-model property on save.
        builder.get_object('menu_button').set_menu_model(builder.get_object('window_menu'))
        builder.get_object('view_button').set_menu_model(builder.get_object('view_menu'))

        self.headerbar = builder.get_object('headerbar')

        self.actions = self.Actions(self, builder)

        self.connect('notify::date', self.date_changed)
        self.date = None  # trigger action updates

    def get_today(self):
        # TODO: handle virtual_midnight
        return datetime.date.today()

    def get_date(self):
        return self.get_today() if self.date is None else self.date

    def get_subtitle(self):
        date = self.get_date()
        return _("{date:%A, %Y-%m-%d} (week {week:0>2})").format(
            date=date, week=date.isocalendar()[1])

    def date_changed(self, obj, param_spec):
        # Enforce strict typing
        if self.date is not None and not isinstance(self.date, datetime.date):
            self.date = None

        # Going back to today clears the date field
        if self.date is not None and self.date >= self.get_today():
            self.date = None

        if self.date is None:
            self.actions.go_home.set_enabled(False)
            self.actions.go_forward.set_enabled(False)
        else:
            self.actions.go_home.set_enabled(True)
            self.actions.go_forward.set_enabled(True)

        self.headerbar.set_subtitle(self.get_subtitle())

    def on_go_back(self, action, parameter):
        self.date = self.get_date() - datetime.timedelta(1)

    def on_go_forward(self, action, parameter):
        self.date = self.get_date() + datetime.timedelta(1)

    def on_go_home(self, action, parameter):
        self.date = None


def main():
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
    sys.exit(app.run(sys.argv))


if __name__ == '__main__':
    main()
