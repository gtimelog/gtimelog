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
configdir = os.path.expanduser('~/.gtimelog')
settings_file = os.path.join(configdir, 'gtimelogrc') 
if os.path.exists(settings_file):
    settings.load(settings_file)
timelog = gtimelog.TimeLog(os.path.join(configdir, 'timelog.txt'),
                           settings.virtual_midnight)
window = timelog.window_for(d1, d2)
window.icalendar(open(outputfile, 'w'))
