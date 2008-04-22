#!/usr/bin/python
import datetime
import readline

f = open("timelog.txt", "a")
print >> f
f.close()

while True:
    try:
        what = raw_input("> ")
    except EOFError:
        print
        break
    ts = datetime.datetime.now()
    line = "%s: %s" % (ts.strftime("%Y-%m-%d %H:%M"), what)
    print line
    f = open("timelog.txt", "a")
    print >> f, line
    f.close()

