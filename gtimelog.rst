========
gtimelog
========

--------------------------------
minimal time logging application
--------------------------------

:Author: Marius Gedminas <mgedmin@gedmin.as>
:Date: 2019-08-05
:Copyright: Marius Gedminas
:Version: 0.12
:Manual section: 1


SYNOPSIS
========

**gtimelog** [options]


DESCRIPTION
===========

``gtimelog`` provides a time tracking application to allow the user to
track what they work on during the day and how long they spend doing it.

Here's how it works: every day, when you arrive to work, start up ``gtimelog``
and type "arrived".  Then start doing some activity (e.g. reading mail, or
working on a task).  Whenever you stop doing an activity (either when you have
finished it, or when you switch to working on something else), type the name
of the activity into the ``gtimelog`` prompt.  Try to use the same text if you
make several entries for an activity (history helps here — just use the up and
down arrow keys).  The key principle is to name the activity after you've
stopped working on it, and not when you've started.  Of course you can type
the activity name upfront, and just delay pressing the Enter key until you're
done.

There are two broad categories of activities: ones that count as work (coding,
planning, writing proposals or reports, answering work-related email), and
ones that don't (browsing the web for fun, reading personal email, chatting
with a friend on the phone for two hours, going out for a lunch break).  To
indicate which activities are not work related add two asterisks to the
activity name::

    lunch **
    browsing slashdot **
    napping on the couch **

If you want some activity (or non-activity) to be completely omitted from the
reports, use three asterisks::

    break ***

``gtimelog`` displays all the things you've done today, calculates the total
time you spent working, and the total time you spent "slacking".  It also
advises you how much time you still have to work today to get 8 hours of
work done, and how much time is left just to have spent a workday at the
office (the number of hours in a day is configurable).

There are three basic views: one shows all the activities in chronological
order, with starting and ending times; another groups all entries with the
same title into one activity and just shows the total duration; and a
third one groups all entries from the same categories into one line with
the total duration.

At the end of the day you can send off a daily report by choosing ``Report...``
from the menu.  You can select a date and a date range (day/week/month) and
preview the report directly in the gtimelog window before sending it.  (Actual
sending requires a working local MTA, such as Postfix, to be installed and
configured, which is outside the scope of this document.)

If you make a mistake and type in the wrong activity name, or just forget to
enter an activity, don't worry.  ``gtimelog`` stores the time log in a simple
plain text file ``~/.gtimelog/timelog.txt`` (or
``~/.local/share/gtimelog/timelog.txt``).  Every line contains a timestamp and
the name of the activity that was finished at the time.  All other lines are
ignored, so you can add comments if you want to — just make sure no comment
begins with a timestamp.  You do not have to worry about ``gtimelog``
overwriting your changes — ``gtimelog`` always appends entries at the end of
the file, and does not keep the log file open all the time.  You do have to
worry about overwriting changes made by ``gtimelog`` with your editor — make
sure you do not enter any activities in ``gtimelog`` while you have
``timelog.txt`` open in a text editor.


OPTIONS
=======

--version
    Show program's version number and exit.

-h, --help
    Show this help message and exit.

--debug
    Show debug information.

--prefs
    Open the preferences window.

--email-prefs
    Open the preferences window on the email page.


FILES
=====

gtimelog uses XDG-compliant config and data directories by default
(~/.config/gtimelog, ~/.local/share/gtimelog).  For backwards compatibility, if
~/.gtimelog exists, it will be used instead.

| **~/.gtimelog/timelog.txt**
| **~/.local/share/gtimelog/timelog.txt**

    Activity log file.  Each line contains an ISO-8601 timestamp
    (YYYY-MM-DD HH:MM:SS) followed by a ":" and a space, followed by the
    activity name.  Lines are sorted chronologically.  Blank lines
    separate days.  Lines starting with ``#`` are comments.

| **~/.gtimelog/tasks.txt**
| **~/.local/share/gtimelog/tasks.txt**

    Tasks to be shown in the task pane.  Each line is either "task name"
    or "category: task name", lines starting with a ``#`` are comments.

| **~/.gtimelog/sentreports.log**
| **~/.local/share/gtimelog/sentreports.log**

    A CSV file listing reports that have been sent.  The columns are:
    timestamp, report kind (daily/weekly/monthly), report date, recipient's
    email address.

| **~/.gtimelog/gtimelogrc**
| **~/.config/gtimelog/gtimelogrc**

    Legacy configuration file for gtimelog 0.10 and older.  If it exists when
    gtimelog 0.11 or newer starts for the first time, settings from it will be
    migrated to gsettings.
