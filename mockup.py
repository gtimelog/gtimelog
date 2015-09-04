#!/usr/bin/python
from __future__ import print_function

import gettext
import locale
import os
import signal
import sys
from gettext import gettext as _

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, Gio, GLib

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

        # The __class__ trick is a bit iffy, but I don't see how else I
        # can define the entire window object in the .ui file.
        builder = Gtk.Builder.new_from_file(UI_FILE)
        builder.add_from_file(MENUS_UI_FILE)
        window = builder.get_object('main_window')
        window.__class__ = Window
        window._init(self, builder)
        self.add_window(window)
        window.show()


class Window(Gtk.ApplicationWindow):

    def _init(self, app, builder):
        # Should I do this?  Nothing bad seems to happen if I don't.
        self.set_application(app)
        self.set_icon_name('gtimelog')

        # Cannot store these in the same .ui file nor hook them up in the
        # .ui because glade doesn't support that and strips both the
        # <menu> and the menu-model property on save.
        builder.get_object('menu_button').set_menu_model(builder.get_object('window_menu'))
        builder.get_object('view_button').set_menu_model(builder.get_object('view_menu'))

        detail_level = Gio.SimpleAction.new_stateful("detail-level", GLib.VariantType.new("s"), GLib.Variant("s", "chronological"))
        self.add_action(detail_level)

        time_range = Gio.SimpleAction.new_stateful("time-range", GLib.VariantType.new("s"), GLib.Variant("s", "day"))
        self.add_action(time_range)

        task_pane = Gio.PropertyAction.new("show-task-pane", builder.get_object("task_pane"), "visible")
        self.add_action(task_pane)

        go_back = Gio.SimpleAction.new("go-back", None)
        self.add_action(go_back)

        go_forward = Gio.SimpleAction.new("go-forward", None)
        go_forward.set_enabled(False)
        self.add_action(go_forward)

        go_home = Gio.SimpleAction.new("go-home", None)
        go_home.set_enabled(False)
        self.add_action(go_home)


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
