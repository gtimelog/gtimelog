GTimeLog Documentation
======================


Overview
========

Here's how it works: every day, when you arrive to work, start up
gtimelog and type "arrived \*\*".  Then start doing some activity (e.g.
reading mail, or working on a task).  Whenever you stop doing an activity
(either when you have finished it, or when you switch to working on
something else), type the name of the activity into the gtimelog prompt.

Try to use the same text if you make several entries for an activity.
History helps here -- type a prefix and then use the
PageUp/PageDown keys to choose the appropriate task.

They key principle here is to name the activity after you've
stopped working on it, and not when you've started.  Of course you can
type the activity name upfront, and just delay pressing the Enter key
until you're done.


Work and rest
=============

There are two kinds of activities: ones that count as billable work
(coding, planning, writing proposals or reports, answering work-related
email), and ones that don't (browsing the web for fun, reading personal
email, chatting with a friend on the phone for two hours, going out for a
lunch break).  To indicate which activities are not work related add two
asterisks to the activity name::

  lunch **
  browsing slashdot **
  napping on the couch **

If you want some activity (or non-activity) to be completely omitted from
the reports, use three asterisks::

  break ***


Categories
==========

Work activities can also include a category name, e.g.::

  project1: fixing bug #1234
  project1: refactoring tessts
  project2: fixing buildbot
  sysadmining: upgrading work laptop

The tasks are grouped by category in the reports.

Each entry may be additionally labelled with multiple
(space-separated) tags, e.g.::

  project3: upgrade webserver -- sysadmin www front-end
  project3: restart mail server -- sysadmin mail

Reports will then include an additional breakdown by tag: for each
tag, the total time spent in entries marked with that tag is shown.
Note that these times will (likely) not add up to the total reporting
time, as each entry may be marked with several tags.

Tags must be separated from the rest of the entry by " -- ", i.e.,
double-dash surrounded by spaces.  Tags will *not* be shown in the
main UI pane.

Back-dating Entries
===================

If you forget to enter an activity, you can enter it after the fact by
prefixing it with a full time ("09:30 morning meeting") or a two digit minute-offset
("-10 morning meeting").  Note that the new activity must still be after
the last entered event, or things will become confusing!


Tasks pane
==========

There's a Tasks pane that lists common tasks.  Click on a task to transfer
it to the input box at the bottom.  Saves typing.

There's a menu option to edit the tasks file.

Tasks are kept in a file named **tasks.txt** in the GTimeLog data
directory (**~/.local/share/gtimelog/** or, for backwards compatibility,
**~/.gtimelog/**).  Feel free to edit it with any text editor of your
choice.  GTimeLog will watch the modification time and reload it
automatically.

There's a hidden option in gsettings for fetching the task list from
an Internet URL.  This way you can use a wiki or something to keep a
shared task list.  The downloaded task list is cached so you can work
offline.  The menu contains an option to fetch an updated version.
Use dconf-editor to enable it (/org/gtimelog, keys remote-task-list,
task-list-url, task-list-edit-url).


Display
=======

GTimeLog displays all the things you've done today, and calculates the
total time you spent working, the total time you spent "slacking", and the
sum total for convenience. It also advises you how much time you still
have to work today to get 8 hours of work done, and how much time is left
just to have spent a workday at the office (the number of hours in a day
is configurable).

There are three basic views: one shows all the activities in chronological
order, with starting and ending times; another groups all entries with the
same title into one activity and just shows the total duration; and a
third one groups all entries from the same categories into one line with
the total duration.

You can use the headerbar buttons or Alt+Left/Right to see what you did on
any previous day.  Hit the Home button (or Alt+Home) to return to today's
view.  Adding a new entry also automatically switches you back to today's
view.


Reports
=======

At the end of the day you can send off a daily report by choosing Report...  in
the menu.  You can select a date and a date range (day/week/month) and preview
the report directly in the gtimelog window before sending it.  (Actual sending
requires a working local MTA, such as Postfix, to be installed and configured,
which is outside the scope of this document.)


Correcting mistakes
===================

If you make a mistake and type in the wrong activity name, don't worry.
GTimeLog stores the time log in a simple plain text file.  You can edit it
by choosing Edit log from the menu (or pressing Ctrl-E).

Every line contains a timestamp and the name of the activity that was
finished at the time.  All other lines are ignored, so you can add comments
if you want to -- just make sure no comment begins with a timestamp.  You don't
have to worry about GTimeLog overwriting your changes -- GTimeLog always
appends entries at the end of the file, and doesn't keep the log file open
all the time.  You do have to worry about overwriting changes made by
GTimeLog with your editor -- make sure you do not enter any activities in
GTimeLog while you have timelog.txt open in a text editor.

GTimeLog watches the modification time and automatically reloads timelog.txt
if it notices you changed it.


Syncing
=======

GTimeLog has no built-in sync between multiple machines.  You can put its
files into Dropbox and create a symlink.

.. include:: footer.rst
