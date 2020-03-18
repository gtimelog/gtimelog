#!/usr/bin/python
import datetime
import readline  # noqa: make raw_input() friendlier
import getopt
import sys
import os

def main(argv=sys.argv):
  filename = 'timelog.txt'
  printnewline = False
  opts, args = getopt.getopt(argv[1:], 'hf:', ['help'])
  for k, v in opts:
    if k == '-f':
      filename = v
    if k == '-n':
      printnewline = True
    if k == '-h':
      print("todo")
      return
  if len(args) > 1:
    print >> sys.stderr, "too many arguments"
    return
  if printnewline:
    f = open(filename, "a")
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
      f = open(filename, "a")
      print >> f, line
      f.close()

if __name__ == '__main__':
    main()
