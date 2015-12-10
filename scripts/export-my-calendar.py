#!/usr/bin/python2.3
"""
Experimental script to export GTimeLog data to iCalendar file.
"""
import os
import datetime
import gtimelog

# Hardcoded date range and output file
d1 = datetime.datetime(2005, 2, 1)
d2 = datetime.datetime.now()
outputfile = 'calendar.ics'

settings = gtimelog.Settings()
configdir = settings.get_config_dir()
datadir = settings.get_data_dir()
settings_file = settings.get_config_file()
if os.path.exists(settings_file):
    settings.load(settings_file)
timelog = gtimelog.TimeLog(settings.get_timelog_file(),
                           settings.virtual_midnight)
window = timelog.window_for(d1, d2)
window.icalendar(open(outputfile, 'w'))
