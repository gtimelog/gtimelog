Data Formats
============

These tools were designed for easy interoperability.  There are two data
formats: one is used for timelog.txt, another is used for daily reports.
They are both human and machine readable, easy to edit, easy to parse.


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
they're not, and it will sort them to compensate (but there are probably bugs
lurking with the computation of ``earliest_timestamp``).

GTimeLog doesn't re-write the file, it only appends to it.

Bugs:

- There's no place for timezones.  If you want to track your travel times
  with GTimeLog, you're gonna have a bad time.
- If you work late at night and change the value of ``virtual_midnight``,
  old historical entries can be misinterpreted.


tasks.txt
---------

Task list is a text file, with one task per line.  Empty lines and lines
starting with a '#' are ignored.  Task names should consist of a group name
(project name, XP-style story, whatever), a colon, and a task name.  Tasks will
be grouped.  If there is no colon on a line, the task will be grouped under
"Other".


Daily reports
-------------

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

