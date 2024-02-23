#!/usr/bin/python
import argparse
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


def format_float_time(t):
    return '%.2f' % (t/60.0)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='Compute the total time in gtimelog rows from stdin.')
    parser.add_argument('-d', '--decimal-output', action='store_true',
                        required=False, help='output time in a decimal format')
    args = parser.parse_args(argv)

    total = 0
    for line in sys.stdin:
        if '  ' not in line:
            continue
        time = parse_time(line.split('  ')[-1].strip())
        if time is None:
            continue
        print line.rstrip()
        total += time

    total_formatted = (format_float_time(total)
                       if args.decimal_output
                       else format_time(total))
    print "** Total: %s" % total_formatted


if __name__ == '__main__':
    main()
