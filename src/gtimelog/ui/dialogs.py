from gettext import gettext as _
from gi.repository import Gtk, GLib, Gio

from gtimelog.paths import PREFERENCES_UI_FILE
from gtimelog.core.utils import parse_time
from gtimelog.ui.services import start_smtp_password_lookup, set_smtp_password
from gtimelog.ui.utils import MAIL_PROTOCOLS


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
