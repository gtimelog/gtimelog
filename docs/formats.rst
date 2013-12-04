Data Formats
============

These tools were designed for easy interoperability.  There are two data
formats: one is used for timelog.txt, another is used for daily reports.
They are both human and machine readable, easy to edit, easy to parse.


timelog.txt
-----------

Here is a more formal grammar::

  file ::= (entry|comment)*

  entry ::= timestamp ":" space title newline

  comment ::= anything* newline

  title ::= anything*

  timestamp is 'YYYY-MM-DD HH:MM' with a single space between the date and
  time.


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

