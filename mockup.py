#!/usr/bin/python

import gi
gi.require_version('Gtk', '3.0')

from gi.repository import Gtk

ui_file = 'src/gtimelog/experiment.ui'

builder = Gtk.Builder.new_from_file(ui_file)

if __name__ == '__main__':
    app = Gtk.Application(application_id='lt.pov.mg.gtimelog_mockup')
    def _activate(app):
        window = builder.get_object('main_window')
        app.add_window(window)
        window.show()
    app.connect('activate', _activate)
    app.run()
