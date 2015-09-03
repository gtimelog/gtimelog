#!/usr/bin/python
import signal

import gi
gi.require_version('Gtk', '3.0')

from gi.repository import Gtk, Gio, GLib

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
        <attribute name="action">app.quit</attribute>
        <attribute name="accel">&lt;Primary&gt;Q</attribute>
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
        <attribute name="action">app.quit</attribute>
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
        <attribute name="action">win.detail-level</attribute>
        <attribute name="target">chronological</attribute>
      </item>
      <item>
        <attribute name="label">Grouped</attribute>
        <attribute name="action">win.detail-level</attribute>
        <attribute name="target">grouped</attribute>
      </item>
      <item>
        <attribute name="label">Summary</attribute>
        <attribute name="action">win.detail-level</attribute>
        <attribute name="target">summary</attribute>
      </item>
    </section>
    <section>
      <item>
        <attribute name="label">Time range</attribute>
        <attribute name="action">disabled</attribute>
      </item>
      <item>
        <attribute name="label">Day</attribute>
        <attribute name="action">win.time-range</attribute>
        <attribute name="target">day</attribute>
      </item>
      <item>
        <attribute name="label">Week</attribute>
        <attribute name="action">win.time-range</attribute>
        <attribute name="target">week</attribute>
      </item>
      <item>
        <attribute name="label">Month</attribute>
        <attribute name="action">win.time-range</attribute>
        <attribute name="target">month</attribute>
      </item>
      <item>
        <attribute name="label">Custom...</attribute>
        <attribute name="action">win.time-range</attribute>
        <attribute name="target">custom</attribute>
      </item>
    </section>
  </menu>
</interface>
'''

builder = Gtk.Builder.new_from_file(ui_file)
builder.add_from_string(menu_def)
builder.get_object('menu_button').set_menu_model(builder.get_object('window_menu'))
builder.get_object('view_button').set_menu_model(builder.get_object('view_menu'))


if __name__ == '__main__':
    app = Gtk.Application(application_id='lt.pov.mg.gtimelog_mockup')
    def _startup(app):
        app.set_app_menu(builder.get_object('app_menu'))
        quit = Gio.SimpleAction.new("quit", None)
        quit.connect('activate', lambda *args: app.quit())
        app.add_action(quit)
        app.set_accels_for_action("win.detail-level('chronological')", ["<Alt>1"])
        app.set_accels_for_action("win.detail-level('grouped')", ["<Alt>2"])
        app.set_accels_for_action("win.detail-level('summary')", ["<Alt>3"])
        app.set_accels_for_action("win.show-task-pane", ["F9"])
        app.set_accels_for_action("win.go-back", ["<Alt>Left"])
        app.set_accels_for_action("win.go-forward", ["<Alt>Right"])
        app.set_accels_for_action("win.go-home", ["<Alt>Home"])
    app.connect('startup', _startup)
    def _activate(app):
        window = builder.get_object('main_window')
        detail_level = Gio.SimpleAction.new_stateful("detail-level", GLib.VariantType.new("s"), GLib.Variant("s", "chronological"))
        window.add_action(detail_level)
        time_range = Gio.SimpleAction.new_stateful("time-range", GLib.VariantType.new("s"), GLib.Variant("s", "day"))
        window.add_action(time_range)
        task_pane = Gio.PropertyAction.new("show-task-pane", builder.get_object("task_pane"), "visible")
        window.add_action(task_pane)
        go_back = Gio.SimpleAction.new("go-back", None)
        window.add_action(go_back)
        go_forward = Gio.SimpleAction.new("go-forward", None)
        go_forward.set_enabled(False)
        window.add_action(go_forward)
        go_home = Gio.SimpleAction.new("go-home", None)
        go_home.set_enabled(False)
        window.add_action(go_home)
        app.add_window(window)
        window.show()
    app.connect('activate', _activate)
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    app.run()
