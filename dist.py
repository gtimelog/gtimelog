#!/usr/bin/env python
"""
Package a release of timelog.

This script is probably completely unsafe, security-wise.  Caveat user.
"""
import os
import shutil

REPOSITORY = "file:///home/mg/svnroot/timelog"

def make_dist():
    try:
        os.mkdir("dist")
    except OSError:
        pass
    os.chdir("dist")
    shutil.rmtree("timelog")

    pipe = os.popen("svn export %s" % REPOSITORY, "r")
    rev = None
    for line in pipe:
        if line.startswith("Exported revision "):
            rev = int(line[len("Exported revision "):].rstrip("\r\n."))
    status = pipe.close()
    if status:
        raise RuntimeError("svn export returned %s" % status)

    pipe = os.popen("svn log -r %d -q %s" % (rev, REPOSITORY), "r")
    last_checkin = pipe.readlines()
    status = pipe.close()
    if status:
        raise RuntimeError("svn log returned %s" % status)
    date = last_checkin[1].split('|')[-1].split('(')[0].strip()

    f = open("timelog/VERSION.txt", "w")
    print >> f, "Revision %d (%s)" % (rev, date)
    f.close()
    os.system("tar -czf timelog-svn%04d.tar.gz timelog" % rev)

if __name__ == "__main__":
    make_dist()
