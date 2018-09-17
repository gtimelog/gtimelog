Data Formats
============

These tools were designed for easy interoperability.  The data formats are
both human and machine readable, easy to edit, easy to parse.

.. contents::


timelog.txt
-----------

Here is a formal grammar::

  file ::= (entry|day-separator|comment|old-style-comment)*

  entry ::= timestamp ":" SPACE title NEWLINE

  day-separator ::= NEWLINE

  comment ::= "#" anything* NEWLINE

  old-style-comment ::= anything* NEWLINE

  title ::= anything*

*timestamp* is ``YYYY-MM-DD HH:MM`` with a single space between the date and
the time.

*anything* is any character except a newline.

*NEWLINE* is whatever Python considers it to be (i.e. CR LF or just LF).

GTimeLog adds a blank line between days.  It ignores them when loading, but
this is likely to change in the future.

GTimeLog considers any lines not starting with a valid timestamp to be
comments.  This is likely to change in the future, so please use '#' to
indicate real comments if you find you need them.

All lines should be sorted by time.  Currently GTimeLog won't complain if
they're not, and it will sort them to compensate.

GTimeLog doesn't re-write the file, it only appends to it.

Example::

  # this is a comment
  2015-09-14 08:03: arrived at work **
  2015-09-14 11:57: project-foo: working on task #1234
  2015-09-14 13:04: lunch **
  2015-09-14 16:34: project-foo: working on task #1234
  2015-09-14 16:57: checking mail

  2015-09-15 08:01: arrived at work **
  ...

Bugs:

- There's no place for timezones.  If you want to track your travel times
  with GTimeLog, you're gonna have a bad time.
- If you work late at night and change the value of "virtual midnight",
  old historical entries can be misinterpreted.


tasks.txt
---------

Task list is a text file, with one task per line.  Empty lines and lines
starting with a '#' are ignored.  Task names should consist of a group name
(project name, XP-style story, whatever), a colon, and a task name.  Tasks will
be grouped.  If there is no colon on a line, the task will be grouped under
"Other".

Example::

  # usual everyday tasks
  mail
  sysadmining
  # project tasks
  project-foo: fix bug with frobnicator (GH: #42)
  project-foo: implement feature X (GH: #123)
  project-bar: daily standup


Daily report emails
-------------------

Daily reports look like this::

  random text
  random text
  Entry title                Duration
  Entry title                Duration
  random text
  Entry title                Duration
  Entry title                Duration
  random text

Formal grammar::

  report ::= (entry|comment)*

  entry ::= title space space duration newline

  comment ::= anything* newline

  title ::= anything*

  duration ::= hours "," space minutes
            |  hours space minutes
            |  hours
            |  minutes

  hours ::= number space "hour"
         |  number space "hours"

  minutes ::= number space "min"

There is a convention that entries that include two asterisks in their titles
indicate slacking or pauses between work activities.


sentreports.log
---------------

This is a comma-separated-value (CSV) file that logs all sent reports.
The columns are: timestamp, report kind (daily/weekly/monthly), report
date, recipient's email address.

Weekly report dates use the ISO week numbering (YYYY/WW).

Example::

    2015-09-09 13:11:41,dayly,2015-09-09,activity@example.com
    2015-09-09 13:12:39,weekly,2015/37,activity@example.com
    2015-09-09 13:12:44,monthly,2015-09,activity@example.com
    2015-09-09 13:12:57,daily,2015-09-09,activity@example.com


.. include:: footer.rst
