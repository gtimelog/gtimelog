#!/usr/bin/python
from __future__ import print_function
import gc
import os
import sys
import time
from operator import itemgetter

pkgdir = os.path.join(os.path.dirname(__file__), 'src')
sys.path.insert(0, pkgdir)

from gtimelog.settings import Settings
from gtimelog.timelog import parse_datetime


fns = []
mark = fns.append


def benchmark(fn):
    gc.collect()
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
    print("\rmin {:.3f}s avg {:.3f}s (n={})\n".format(m, tot / n, n))


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
def parse_one():
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
def parse_two():  # slower than parse_one
    filename = Settings().get_timelog_file()
    for line in open(filename):
        try:
            time, entry = line.split(': ', 1)
            time = parse_datetime(time)
        except ValueError:
            continue


@mark
def parse_three():  # fastest
    filename = Settings().get_timelog_file()
    for line in open(filename):
        time, sep, entry = line.partition(': ')
        if not sep:
            continue
        try:
            time = parse_datetime(time)
        except ValueError:
            continue


@mark
def parse_and_strip():
    filename = Settings().get_timelog_file()
    for line in open(filename):
        time, sep, entry = line.partition(': ')
        if not sep:
            continue
        try:
            time = parse_datetime(time)
        except ValueError:
            continue
        entry = entry.strip()


@mark
def parse_and_collect():
    items = []
    filename = Settings().get_timelog_file()
    for line in open(filename):
        time, sep, entry = line.partition(': ')
        if not sep:
            continue
        try:
            time = parse_datetime(time)
        except ValueError:
            continue
        entry = entry.strip()
        items.append((time, entry))


@mark
def parse_and_sort_incorrectly():
    items = []
    filename = Settings().get_timelog_file()
    for line in open(filename):
        time, sep, entry = line.partition(': ')
        if not sep:
            continue
        try:
            time = parse_datetime(time)
        except ValueError:
            continue
        entry = entry.strip()
        items.append((time, entry))
    items.sort()  # XXX: can reorder lines


@mark
def parse_and_sort_correctly():
    items = []
    filename = Settings().get_timelog_file()
    for line in open(filename):
        time, sep, entry = line.partition(': ')
        if not sep:
            continue
        try:
            time = parse_datetime(time)
        except ValueError:
            continue
        entry = entry.strip()
        items.append((time, entry))
    items.sort(key=itemgetter(0))


@mark
def full():
    Settings().get_time_log()


def main():
    for fn in fns:
        benchmark(fn)


if __name__ == '__main__':
    main()
