#!/usr/bin/python
"""
Given a constraint to do at least 7 hours of work per day, how many actual
days of work you did in a given week?
"""

import fileinput
import re

time_rx = re.compile(r'(\d+) hours?,? (\d+) min$'
                     r'|(\d+) hours?$'
                     r'|(\d+) min$')

def parse_time(s):
    m = time_rx.match(s)
    if not m:
        return None
    h1, m1, h2, m2 = m.groups()
    return int(h1 or h2 or '0') * 60 + int(m1 or m2 or '0')


def format_time(t):
    h, m = divmod(t, 60)
    if h and m:
        return '%d hour%s, %d min' % (h, h != 1 and "s" or "", m)
    elif h:
        return '%d hour%s' % (h, h != 1 and "s" or "")
    else:
        return '%d min' % m


def main():
    for line in fileinput.input():
        if line.startswith('Total work done this week:'):
            work_in_minutes = parse_time(line.split(':', 1)[1].strip())
            assert work_in_minutes is not None
            print line,
            break
    else:
        return

    work_days = 5.0
    days_off = 0
    while True:
        avg_day_len = work_in_minutes / work_days
        if avg_day_len >= 6 * 60 + 50:
            break
        days_off += 0.5
        work_days -= 0.5
    def fmt(f):
        return ("%.1f" % f).replace(".0", "")
    print "  Days off: %s" % fmt(days_off)
    print "  Work days: %s" % fmt(work_days)
    print "  Average day length: %s" % format_time(avg_day_len)


if __name__ == '__main__':
    main()
