#!/usr/bin/python
import argparse
import os
from sum import parse_time


FIELD_DELIMITER = ';'


def format_decimal_time(t):
    return '%.2f hours' % round(t/60.0, 2)


def format_pseudo_iso_time(t):
    """Return a hh:mm:ss time where hh may be > 24"""
    hours = t / 60
    minutes = t % 60
    return '%d:%d:00' % (hours, minutes)


def format_line(line):
    """Prepare a line for import into XLS"""
    if '  ' not in line:
        return line
    pieces = line.split('  ')
    desc = ' '.join(pieces[:-1])
    time = parse_time(pieces[-1].strip())
    if time is None:
        return line
    return '%s %s %s' % (desc, FIELD_DELIMITER, format_pseudo_iso_time(time))


def format_file(input_file, output_file):
    """Read an input_file object and output it formatted into output_file object."""
    for line in input_file:
        formatted = format_line(line)
        output_file.write('%s\n' % formatted)


def choose_output_file_name(input_file, output_file):
    name = output_file
    if not name:
        base, ext = os.path.splitext(input_file)
        name = '%s.csv' % base

    candidate = name
    iterator = 0
    while os.path.exists(candidate):
        iterator += 1
        base, ext = os.path.splitext(name)
        candidate = '%s(%d)%s' % (base, iterator, ext)

    return candidate


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Prepare gtimelog rows for import into XLS')
    parser.add_argument(
        'input_file',
        help='an <input_file>.txt that contains gtimelog report lines')
    parser.add_argument(
        'output_file', nargs='?',
        help='an <output_file> to create; the default is <input_file.csv>')

    args = parser.parse_args()
    input_file = args.input_file
    output_file = choose_output_file_name(input_file, args.output_file)

    return input_file, output_file


if __name__ == '__main__':

    input_file, output_file = parse_arguments()

    input_file = open(input_file, mode='r')
    output_file = open(output_file, mode='w+')

    format_file(input_file, output_file)

    input_file.close()
    output_file.close()
