#!/usr/bin/python

import re
import os
import sys
import getopt
import datetime

def read_timelog(filename):
    return file(filename)

def todays_entries(today, lines):
    # assume "day turnover" at 2 am
    min = datetime.datetime.combine(today, datetime.time(2, 0))
    max = min + datetime.timedelta(1)
    for line in lines:
        time = line.split(': ', 1)[0]
        try:
            time = parse_datetime(time)
        except ValueError:
            pass
        else:
            if min <= time < max:
                yield line

def parse_date(dt):
    m = re.match(r'^(\d+)-(\d+)-(\d+)$', dt)
    if not m:
        raise ValueError('bad date: ', dt)
    year, month, day = map(int, m.groups())
    return datetime.date(year, month, day)

def parse_datetime(dt):
    m = re.match(r'^(\d+)-(\d+)-(\d+) (\d+):(\d+)$', dt)
    if not m:
        raise ValueError('bad date time: ', dt)
    year, month, day, hour, min = map(int, m.groups())
    return datetime.datetime(year, month, day, hour, min)

def calculate_diffs(lines):
    last_time = None
    for line in lines:
        time, action = line.split(': ', 1)
        time = parse_datetime(time)
        if last_time is None:
            delta = None
        else:
            delta = time - last_time
        yield last_time, time, delta, action.strip()
        last_time = time

def format_time(t):
    h, m = divmod(t, 60)
    if h and m:
        return '%d hour%s %d min' % (h, h != 1 and "s" or "", m)
    elif h:
        return '%d hour%s' % (h, h != 1 and "s" or "")
    else:
        return '%d min' % m

def print_diff(last_time, time, delta, action):
    time = time.strftime('%H:%M')
    if delta is None:
        delta = ""
    else:
        delta = format_time(delta.seconds / 60)

    # format 1
    ## print "%s%15s  %s" % (time, delta, action)

    # format 2
    action = action[:1].title() + action[1:]
    if not delta:
        print "%s at %s\n" % (action, time)
    else:
        print "%-62s  %s" % (action, delta)

def print_diffs(iter):
    first_time = None
    time = None
    total_time = total_slack = datetime.timedelta(0)
    for last_time, time, delta, action in iter:
        if first_time is None:
            first_time = time
        print_diff(last_time, time, delta, action)
        if delta is not None:
            if '**' in action:
                total_slack += delta
            else:
                total_time += delta
    return first_time, time, total_time, total_slack


def main(argv=sys.argv):
    filename = 'timelog.txt'
    opts, args = getopt.getopt(argv[1:], 'hf:', ['help'])
    for k, v in opts:
        if k == '-f':
            filename = v
    if len(args) > 1:
        print >> sys.stderr, "too many arguments"
    elif len(args) == 1:
        if args[0] == 'yesterday':
            today = datetime.date.today() - datetime.timedelta(1)
        else:
            today = parse_date(args[0])
    else:
        if os.path.basename(argv[0]).replace('.py', '') == 'yesterday':
            today = datetime.date.today() - datetime.timedelta(1)
        else:
            today = datetime.date.today()

    title = "Today, %s" % today.strftime('%Y-%m-%d')
    print title
    print "-" * len(title)
    chain = read_timelog(filename)
    chain = todays_entries(today, chain)
    chain = calculate_diffs(chain)
    first_time, last_time, total_time, total_slack = print_diffs(chain)

    now = datetime.datetime.now()
    print ""
    print "Total work done: %s" % format_time(total_time.seconds / 60)
    print "Time spent slacking: %s" % format_time(total_slack.seconds / 60)
    print ""
    print "Time now: %s" % now.strftime('%H:%M')
    if last_time is not None:
        delta = now - last_time
        print "Time since last entry: %s" % format_time(delta.seconds / 60)
        delta = now - first_time
        print "Time since first entry: %s" % format_time(delta.seconds / 60)
        est_end_of_work = last_time + datetime.timedelta(hours=8) - total_time
        delta = est_end_of_work - now
        print "Time left at work: %s (til %s)" % (
                format_time(delta.seconds / 60),
                est_end_of_work.strftime("%H:%M"))


if __name__ == '__main__':
    main()
