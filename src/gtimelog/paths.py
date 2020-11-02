"""
Resource locations for running out of source checkouts and pip installs
"""

import os
import subprocess
import sys


here = os.path.dirname(__file__)

SCHEMA_DIR = os.path.join(here, 'data')
if SCHEMA_DIR and not os.environ.get('GSETTINGS_SCHEMA_DIR'):
    # Have to do this before importing 'gi'.
    # Note: it has been brought to my attention that I can do
    #   source = Gio.SettingsSchemaSource.new_from_directory(SCHEMA_DIR,
    #       Gio.SettingsSchemaSource.get_default(), False)
    #   schema = source.lookup('...', False)
    # to load schemas from any location
    os.environ['GSETTINGS_SCHEMA_DIR'] = SCHEMA_DIR
    if not os.path.exists(os.path.join(SCHEMA_DIR, 'gschemas.compiled')):
        # This, too, I have to do before importing 'gi'.
        print("Compiling GSettings schema")
        glib_compile_schemas = os.path.join(sys.prefix, 'lib', 'site-packages', 'gnome', 'glib-compile-schemas.exe')
        if not os.path.exists(glib_compile_schemas):
            glib_compile_schemas = 'glib-compile-schemas'
        try:
            subprocess.call([glib_compile_schemas, SCHEMA_DIR])
        except OSError as e:
            print("Failed: %s" % e)


ui_dir = here

UI_FILE = os.path.join(ui_dir, 'gtimelog.ui')
PREFERENCES_UI_FILE = os.path.join(ui_dir, 'preferences.ui')
ABOUT_DIALOG_UI_FILE = os.path.join(ui_dir, 'about.ui')
SHORTCUTS_UI_FILE = os.path.join(ui_dir, 'shortcuts.ui')
MENUS_UI_FILE = os.path.join(ui_dir, 'menus.ui')
CSS_FILE = os.path.join(ui_dir, 'gtimelog.css')

LOCALE_DIR = os.path.join(here, 'locale')
CONTRIBUTORS_FILE = os.path.join(here, 'CONTRIBUTORS.rst')
