from __future__ import print_function

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

import gtimelog


class CollaboraExtension(object):

    def init(self):
        gtimelog.hooks['before-gtk-main'].append(self.before_gtk_main)
        gtimelog.hooks['ui'].append(self.ui)

    def before_gtk_main(self):
        print('Testing hook')

    def ui(self, main_window, builder, resource_dir):
        print('Hook called')
        menu_item = Gtk.MenuItem(label='Testing')
        print(menu_item)
        menu_item.show()

        menu_item.connect('activate', lambda widget: print('menu modified'))

        report_menu = builder.get_object('menuitem2_menu')
        report_menu.prepend(menu_item)
        print('prepended')

ce = CollaboraExtension()
def init():
    print('Collabora gtimelog extension module init')
    ce.init()
