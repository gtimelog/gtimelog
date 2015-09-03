#!/usr/bin/python
import signal

import gi
gi.require_version('Gtk', '3.0')

from gi.repository import Gtk, GObject

ui_file = 'src/gtimelog/experiment.ui'
menu_def = '''
<interface>
  <menu id="app_menu">
    <section>
      <item>
        <attribute name="label">Help</attribute>
      </item>
      <item>
        <attribute name="label">About</attribute>
      </item>
    </section>
    <section>
      <item>
        <attribute name="label">Quit</attribute>
      </item>
    </section>
  </menu>
  <menu id="window_menu">
    <section>
      <item>
        <attribute name="label">Edit timelog.txt</attribute>
      </item>
    </section>
    <section>
      <item>
        <attribute name="label">Quit</attribute>
      </item>
    </section>
  </menu>
  <menu id="view_menu">
    <section>
      <item>
        <attribute name="label">Detail level</attribute>
        <attribute name="action">disabled</attribute>
      </item>
      <item>
        <attribute name="label">Chronological</attribute>
      </item>
      <item>
        <attribute name="label">Grouped</attribute>
      </item>
      <item>
        <attribute name="label">Summary</attribute>
      </item>
    </section>
  </menu>
</interface>
'''

builder = Gtk.Builder.new_from_file(ui_file)
builder.add_from_string(menu_def)
builder.get_object('menu_button').set_menu_model(builder.get_object('window_menu'))
builder.get_object('view_button').set_menu_model(builder.get_object('view_menu'))
builder.get_object('task_pane_button').bind_property("active", builder.get_object('task_pane'), "visible", GObject.BindingFlags.BIDIRECTIONAL)

if __name__ == '__main__':
    app = Gtk.Application(application_id='lt.pov.mg.gtimelog_mockup')
    def _startup(app):
        app.set_app_menu(builder.get_object('app_menu'))
    app.connect('startup', _startup)
    def _activate(app):
        window = builder.get_object('main_window')
        app.add_window(window)
        window.show()
    app.connect('activate', _activate)
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    app.run()
