Old scripts
===========

These old scripts are kept for sentimental value.

timelog.py is an earlier, less powerful text-mode version of gtimelog.  You
type in activity names, and timelog writes them down into timelog.txt with
timestamps prepended.

today.py can generate a daily report from timelog.txt.  It does not group
activities with the same name, and it does not spawn a mail client.
You can also specify the date on the command line -- generating reports for
earlier days is not yet possible with GTimeLog.

sum.py can help you consolidate daily reports.  It is designed to work as a
filter: it reads lines from the standard input, extracts durations from
those lines (formatted as "N hours, M min" at the end of the line, and
separated by at least two spaces from other text), sums them and prints the
total.  If you use vim for editing daily reports, you can select a bunch of
lines and pipe them through sum.py.

difftime.py is a hacky interactive calculator that I used to generate daily
reports from timelog.txt before today.py and gtimelog.py could automate the
task.  The biggest feature of difftime.py (it's raison d'etre if you will)
is the ability to calculate the duration between two timestamps.

export-my-calendar.py uses the gtimelog internal APIs to produce an iCalendar
file of the log.  It has some hardcoded dates.
