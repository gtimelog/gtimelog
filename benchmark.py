#!/usr/bin/python3

import gc
import os
import sys
import time
from operator import itemgetter


pkgdir = os.path.join(os.path.dirname(__file__), 'src')
sys.path.insert(0, pkgdir)

from gtimelog.settings import Settings
from gtimelog.timelog import TimeLog, parse_datetime


fns = []


def mark(fn):
    fns.append(fn)
    return fn


def unmark(fn):
    return fn


def benchmark(fn, correct_output):
    gc.collect()
    print("{}:".format(fn.__name__), end="")
    m = float("inf")
    n = 0
    output = fn()
    if output != correct_output:
        print(" [NB incorrect output]")
    else:
        print()
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


@unmark
def just_read():
    filename = Settings().get_timelog_file()
    open(filename).readlines()


@unmark
def split():
    filename = Settings().get_timelog_file()
    for line in open(filename):
        if ': ' not in line:
            continue
        time, entry = line.split(': ', 1)


@unmark
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


@unmark
def parse_two():  # slower than parse_one
    filename = Settings().get_timelog_file()
    for line in open(filename):
        try:
            time, entry = line.split(': ', 1)
            time = parse_datetime(time)
        except ValueError:
            continue


@unmark
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


@unmark
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


@unmark
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
    return items


@unmark
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
    return items


@mark
def parse_and_sort():
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
    return items


@mark
def parse_and_sort_unicode():
    items = []
    filename = Settings().get_timelog_file()
    for line in open(filename, 'rb').read().decode('UTF-8').splitlines():
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
    return items


@unmark
def parse_and_sort_unicode_piecemeal():
    items = []
    filename = Settings().get_timelog_file()
    for line in open(filename, 'rb'):
        time, sep, entry = line.partition(b': ')
        if not sep:
            continue
        try:
            time = parse_datetime(time.decode('ASCII'))
        except (ValueError, UnicodeError):
            continue
        entry = entry.strip().decode('UTF-8')
        items.append((time, entry))
    items.sort(key=itemgetter(0))
    return items


@mark
def parse_and_sort_python3():
    items = []
    filename = Settings().get_timelog_file()
    for line in open(filename, 'r', encoding='UTF-8'):
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
    return items


@mark
def full():
    return TimeLog(Settings().get_timelog_file(), Settings().virtual_midnight).items


def main():
    correct = full()
    for fn in fns:
        benchmark(fn, correct)


if __name__ == '__main__':
    main()
