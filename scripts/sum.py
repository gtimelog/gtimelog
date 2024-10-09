#!/usr/bin/python3
import argparse
import re
import sys


time_rx = re.compile(r'(\d+) hours?,? (\d+) min$'
                     r'|(\d+) hours?$'
                     r'|(\d+) min$'
                     r'|(\d\d+):(\d\d)$')


def parse_time(s):
    m = time_rx.match(s)
    if not m:
        return None
    h1, m1, h2, m2, h3, m3 = m.groups()
    return int(h1 or h2 or h3 or '0') * 60 + int(m1 or m2 or m3 or '0')


def parse_time_line(line):
    if '  ' in line:
        return parse_time(line.rpartition('  ')[-1])
    elif ' ' in line:
        return parse_time(line.rpartition(' ')[-1])
    else:
        return None


def format_time(t):
    h, m = divmod(t, 60)
    if h and m:
        return '%d hour%s, %d min' % (h, h != 1 and "s" or "", m)
    elif h:
        return '%d hour%s' % (h, h != 1 and "s" or "")
    else:
        return '%d min' % m


parser = argparse.ArgumentParser(description="sum time entries")
parser.add_argument(
    "-d", "--decimal", action="store_true",
    help="output decimal hours (12.3) instead of hours and minutes")
parser.add_argument(
    "--test", action="store_true",
    help=argparse.SUPPRESS)


def main():
    args = parser.parse_args()
    if args.test:
        test_parse_time()
        sys.exit()

    total = 0
    for line in sys.stdin:
        line = line.rstrip()
        time = parse_time_line(line)
        if time is None:
            continue
        print(line)
        total += time

    if args.decimal:
        print("** Total: %.2f hours" % (total / 60.0))
    else:
        print("** Total: %s" % format_time(total))


def test_parse_time():
    assert parse_time('1 hour 42 min') == 102
    assert parse_time('1 hour') == 60
    assert parse_time('42 min') == 42
    assert parse_time('01:42') == 102
    assert parse_time_line('task task 01:42') == 102
    assert parse_time_line('task task  1 hour 42 min') == 102


if __name__ == "__main__":
    main()
