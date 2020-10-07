"""
UI components utils
"""
import os
import sys
import collections
import smtplib
from gettext import gettext as _
import gi
from gi.repository import Gtk, GLib, GObject, Gio, Gdk

from gtimelog import __version__
from gtimelog.core.settings import Settings
from gtimelog.core.utils import as_minutes
from gtimelog.core.reports import ReportRecord
from gtimelog.main import root_logger

log = root_logger.getChild('application')


MailProtocol = collections.namedtuple('MailProtocol', 'factory, startssl')
MAIL_PROTOCOLS = {
    'SMTP': MailProtocol(smtplib.SMTP, False),
    'SMTPS': MailProtocol(smtplib.SMTP_SSL, False),
    'SMTP (StartTLS)': MailProtocol(smtplib.SMTP, True),
}
REPORT_KINDS = {
    # map time_range values to report_kind values
    'day': ReportRecord.DAILY,
    'week': ReportRecord.WEEKLY,
    'month': ReportRecord.MONTHLY,
}


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


def copy_properties(src, dest):
    blacklist = (
        'events', 'child', 'parent', 'input-hints', 'buffer', 'tabs',
        'completion', 'model', 'type',
        'progress-', 'primary-icon-', 'secondary-icon-',
    )
    read_write = GObject.ParamFlags.READWRITE
    for prop in src.props:
        if prop.flags & GObject.ParamFlags.DEPRECATED != 0:
            continue
        if prop.flags & read_write != read_write:
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


def internationalised_format_duration(duration):
    """Format a datetime.timedelta with minute precision.

    The difference from gtimelog.core.utils.format_duration() is that this
    one is internationalized.
    """
    h, m = divmod(as_minutes(duration), 60)
    return _('{0} h {1} min').format(h, m)


def check_schema():
    schema_source = Gio.SettingsSchemaSource.get_default()
    if schema_source.lookup("org.gtimelog", False) is None:
        sys.exit(_("\nWARNING: GSettings schema for org.gtimelog is missing!  "
                   "If you're running from a source checkout, be sure to run 'make'."))


def create_data_directory():
    data_dir = Settings().get_data_dir()
    if not os.path.exists(data_dir):
        try:
            os.makedirs(data_dir)
        except OSError as e:
            log.error(_("Could not create {directory}: {error}").format(directory=data_dir, error=e), file=sys.stderr)
        else:
            log.info(_("Created {directory}").format(directory=data_dir))


def do_handle_local_options(options):
    if options.contains('version'):
        print(_('GTimeLog version: {}').format(__version__))
        print(_('Python version: {}').format(sys.version.replace('\n', '')))
        print(_('GTK+ version: {}.{}.{}').format(Gtk.MAJOR_VERSION, Gtk.MINOR_VERSION, Gtk.MICRO_VERSION))
        print(_('PyGI version: {}').format(gi.__version__))
        print(_('Data directory: {}').format(Settings().get_data_dir()))
        print(_('Legacy config directory: {}').format(Settings().get_config_dir()))
        check_schema()
        gsettings = Gio.Settings.new("org.gtimelog")
        if not gsettings.get_boolean('settings-migrated'):
            print(_('Settings will be migrated to GSettings (org.gtimelog) on first launch'))
        else:
            print(_('Settings already migrated to GSettings (org.gtimelog)'))
        return 0
    return -1  # send the args to the remote instance for processing


def are_there_any_modals():
    # Fix for https://github.com/gtimelog/gtimelog/issues/127
    return any(window.get_modal() for window in Gtk.Window.list_toplevels())


def open_in_editor(filename):
    if not os.path.exists(filename):
        open(filename, 'a').close()
    if os.name == 'nt':
        os.startfile(filename)
    else:
        uri = GLib.filename_to_uri(filename, None)
        Gtk.show_uri(None, uri, Gdk.CURRENT_TIME)
