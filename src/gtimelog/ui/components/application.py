from gettext import gettext as _
from gi.repository import Gtk, Gdk, GLib, Gio

from gtimelog import __version__
from gtimelog.main import root_logger
from gtimelog.paths import CSS_FILE, MENUS_UI_FILE, SHORTCUTS_UI_FILE, ABOUT_DIALOG_UI_FILE
from gtimelog.core.settings import Settings
from gtimelog.core.utils import mark_time, get_contributors
from gtimelog.ui.components.dialogs import PreferencesDialog
from gtimelog.ui.components.utils import make_option, check_schema, create_data_directory, are_there_any_modals,\
    open_in_editor
from gtimelog.ui.components.windows import Window

log = root_logger.getChild('application')


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
        self.actions = self.Actions(self)
        GLib.set_application_name(_("Time Log"))
        GLib.set_prgname('gtimelog')
        self.add_main_option_entries([
            make_option("--version", description=_("Show version number and exit")),
            make_option("--debug", description=_("Show debug information on the console")),
            make_option("--prefs", description=_("Open the preferences dialog")),
            make_option("--email-prefs", description=_("Open the preferences dialog on the email page")),
        ])

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

        check_schema()
        create_data_directory()

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

        self.set_accels_for_action("win.detail-level::chronological", ["<Alt>1"])
        self.set_accels_for_action("win.detail-level::grouped", ["<Alt>2"])
        self.set_accels_for_action("win.detail-level::summary", ["<Alt>3"])
        self.set_accels_for_action("win.time-range::day", ["<Alt>4"])
        self.set_accels_for_action("win.time-range::week", ["<Alt>5"])
        self.set_accels_for_action("win.time-range::month", ["<Alt>6"])
        self.set_accels_for_action("win.show-task-pane", ["F9"])
        self.set_accels_for_action("win.show-menu", ["F10"])
        self.set_accels_for_action("win.show-search-bar", ["<Primary>F"])
        self.set_accels_for_action("win.go-back", ["<Alt>Left"])
        self.set_accels_for_action("win.go-forward", ["<Alt>Right"])
        self.set_accels_for_action("win.go-home", ["<Alt>Home"])
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

    def on_edit_log(self, action, parameter):
        filename = Settings().get_timelog_file()
        open_in_editor(filename)

    def on_edit_tasks(self, action, parameter):
        gsettings = Gio.Settings.new("org.gtimelog")
        if gsettings.get_boolean('remote-task-list'):
            uri = gsettings.get_string('task-list-edit-url')
            if self.get_active_window() is not None:
                self.get_active_window().editing_remote_tasks = True
            Gtk.show_uri(None, uri, Gdk.CURRENT_TIME)
        else:
            filename = Settings().get_task_list_file()
            open_in_editor(filename)

    def on_refresh_tasks(self, action, parameter):
        gsettings = Gio.Settings.new("org.gtimelog")
        if gsettings.get_boolean('remote-task-list'):
            if self.get_active_window() is not None:
                self.get_active_window().download_tasks()

    def on_shortcuts(self, action, parameter):
        builder = Gtk.Builder.new_from_file(SHORTCUTS_UI_FILE)
        shortcuts_window = builder.get_object('shortcuts_window')
        shortcuts_window.set_transient_for(self.get_active_window())
        shortcuts_window.show_all()

    def on_about(self, action, parameter):
        # Note: must create a new dialog (which means a new Gtk.Builder)
        # on every invocation.
        builder = Gtk.Builder.new_from_file(ABOUT_DIALOG_UI_FILE)
        about_dialog = builder.get_object('about_dialog')
        about_dialog.set_version(__version__)
        about_dialog.set_authors(get_contributors())
        about_dialog.set_transient_for(self.get_active_window())
        about_dialog.connect("response", lambda *args: about_dialog.destroy())
        about_dialog.show()

    def on_preferences(self, action=None, parameter=None, page=None):
        if are_there_any_modals():
            # Don't let a user invoke this recursively via gtimelog --prefs
            return
        preferences = PreferencesDialog(self.get_active_window(), page=page)
        preferences.connect("response", lambda *args: preferences.destroy())
        preferences.run()

    def do_activate(self):
        mark_time("in app activate")
        window = self.get_active_window()
        if window is not None:
            # window.present() doesn't work on wayland:
            # https://gitlab.gnome.org/GNOME/gtk/issues/624#note_119092
            window.present_with_time(GLib.get_monotonic_time() // 1000)
            return

        window = Window(self)
        mark_time("have window")
        self.add_window(window)
        mark_time("added window")
        window.show()
        mark_time("showed window")

        GLib.idle_add(mark_time, "in main loop")

        mark_time("app activate done")
