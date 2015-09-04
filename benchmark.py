#!/usr/bin/python
from __future__ import print_function
import os
import sys
import time

pkgdir = os.path.join(os.path.dirname(__file__), 'src')
sys.path.insert(0, pkgdir)

from gtimelog.settings import Settings
from gtimelog.timelog import parse_datetime


fns = []
mark = fns.append


def benchmark(fn):
    print("{}:".format(fn.__name__))
    m = float("inf")
    n = 0
    t00 = time.time()
    while n < 3 or time.time() - t00 < 3:
        t0 = time.time()
        fn()
        t1 = time.time()
        d = t1 - t0
        m = min(m, d)
        print("\r{:.3f}s".format(d), end="")
        sys.stdout.flush()
        n += 1
        if n > 100:
            break
    tot = time.time() - t00
    print("\rmin {:.3f}s avg {:.3f}s\n".format(m, tot / n))


@mark
def just_read():
    filename = Settings().get_timelog_file()
    open(filename).readlines()


@mark
def split():
    filename = Settings().get_timelog_file()
    for line in open(filename):
        if ': ' not in line:
            continue
        time, entry = line.split(': ', 1)

@mark
def parse():
    filename = Settings().get_timelog_file()
    for line in open(filename):
        if ': ' not in line:
            continue
        time, entry = line.split(': ', 1)
        try:
            time = parse_datetime(time)
        except ValueError:
            continue


@mark
def full():
    Settings().get_time_log()


def main():
    for fn in fns:
        benchmark(fn)


if __name__ == '__main__':
    main()
