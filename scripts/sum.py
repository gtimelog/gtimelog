#!/usr/bin/python
import sys
import re


time_rx = re.compile(r'(\d+) hours?,? (\d+) min$'
                     r'|(\d+) hours?$'
                     r'|(\d+) min$'
                     r'|(\d+) h (\d+) min$'
                     r'|(\d+):(\d+)$'
                     )


def parse_time(s):
    m = time_rx.match(s)
    if not m:
        return None
    h1, m1, h2, m2, h3, m3, h4, m4 = m.groups()
    return int(h1 or h2 or h3 or h4 or '0') * 60 + int(m1 or m2 or m3 or m4 or '0')


def format_time(t):
    h, m = divmod(t, 60)
    if h and m:
        return '%d hour%s, %d min' % (h, h != 1 and "s" or "", m)
    elif h:
        return '%d hour%s' % (h, h != 1 and "s" or "")
    else:
        return '%d min' % m


total = 0
for line in sys.stdin:
    if '  ' not in line:
        continue
    time = parse_time(line.split('  ')[-1].strip())
    if time is None:
        continue
    print line.rstrip()
    total += time

print "** Total: %s" % format_time(total)
