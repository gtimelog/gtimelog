==========
gtimelogrc
==========

---------------------------
gtimelog configuration file
---------------------------


:Author: Marius Gedminas <mgedmin@gedmin.as>
:Date: 2013-12-23
:Copyright: Marius Gedminas
:Version: 0.9.1
:Manual section: 5


DESCRIPTION
===========

This is the configuration file for **gtimelog**\ (1).  It is a pretty standard
INI file as recognized by Python's ConfigParser, which means:

- it consists of sections, led by a ``[name]`` header
- values are specified as ``name = value`` (or ``name: value``)
- values can be continued across multiple lines if continuation lines
  start with whitespace
- comments are lines starting with ``#`` or ``;``
- if the same value appears multiple times, new appearances override old ones

Only one section is important to gtimelog: ``[gtimelog]``.  Within it you can
specify the following settings:


list-email
    recipient address for activity reports

    Example: ``name = activity-reports@example.com``

name
    your name as it should appear in the reports

    Example: ``name = Marius``

mailer
    command to launch your email client.

    If ``%s`` appears in the command, it will be replaced by the filename of
    the draft of the email.  If ``%s`` doesn't appear, it will be added to the
    end of the command.

    Example: ``mailer = gedit`` will just open the report in GEdit,
    useful if you don't want to send it to anyone.

    Example: ``mailer = x-terminal-emulator -e mutt -H %s`` (which is the
    default setting) will open Mutt with the draft in a terminal.
    ``x-terminal-emulator`` is a Debianism.

    Example: ``mailer = S='%s'; thunderbird -compose "to='$(cat $S|head -1|sed -e "s/^To: //")',subject='$(cat $S|head -2|tail -1|sed -e "s/^Subject: //")',body='$(cat $S|tail -n +4)'"``
    will open Thunderbird with the draft.

editor
    text editor to be used for editing timelog.txt

    If ``%s`` appears in the command, it will be replaced by the filename of
    the timelog.txt file.  If ``%s`` doesn't appear, it will be added to the
    end of the command.

    Example: ``editor = xdg-open`` (the default value) opens whichever
    program is associated with .txt files on your system.

spreasheet
    program used to display CSV reports

    If ``%s`` appears in the command, it will be replaced by the filename of
    the CSV report.  If ``%s`` doesn't appear, it will be added to the end of
    the command.

    Example: ``spreadsheet = xdg-open`` (the default value) opens whichever
    program is associated with .csv files on your system.

chronological, summary_view
    select the initial detail level

    GTimeLog can show you one of three detail levels:

    - chronological (Alt+1) shows all the entries in order
    - grouped (Alt+2) shows only work entries, grouped by title
    - summary (Alt+3) shows only categories of work entries, grouped

    Example::

      # start in chronological view
      chronological = True
      summary_view = False

    Example ::

      # start in grouped view
      chronological = False
      summary_view = False

    Example ::

      # start in summary view
      summary_view = True

show_tasks
    should the task pane be shown on startup?

    Example: ``show_tasks = True``

enable_gtk_completion
    should the input box show an autocompletion popup?

    If set to ``True``, the Up and Down keys navigate the completion popup
    menu.

    If set to ``False``, the Up and Down keys trigger prefix-completion in the
    input box.

    Note that PageUp and PageDown keys always trigger prefix-completion, so
    there's no good reason to ever disable this option.

    Example: ``enable_gtk_completion = True``

hours
    goal for the number of hours of work in a day

    This is used to display the "Time left at work" estimate.

    Example: ``hours = 4``

virtual_midnight
    hour in the morning when it's safe to assume you're not staying up working
    any more.

    Any work done between midnight and "virtual midnight" will be attributed
    to the previous calendar day.

    Example: ``virtual_midnight = 2:00`` (the default setting)

    Warning: changing this setting may mean that old reports can no longer be
    correctly reconstructed from timelog.txt

task_list_url
    URL for downloading the task list

    If not set, tasks will be read from a local file (tasks.txt in the gtimelog
    data directory)

    If set, tasks will be loaded from the specified URL (but only when you
    right-click and explicitly ask for a refresh).  GTimeLog expects a
    text/plain response with a list of tasks, one per line.  At the time of
    this writing GTimeLog doesn't show HTTP authentication prompts, so if you
    need auth, you need to put your username and password into the URL.

    This feature is mostly useless.

    Example: ``task_list_url =`` (the default setting)

    Example: ``task_list_url = https://wiki.example.com/Project/Tasks/raw``

edit_tasklist_cmd
    command for editing the task list

    Example: ``edit_tasklist_cmd =`` (the default setting)  means that the
    "Edit task list" command in the popup menu will be disabled.

    Example: ``edit_tasklist_cmd = xdg-open ~/.local/share/gtimelog/tasks.txt``

    Example: ``edit_tasklist_cmd = xdg-open https://wiki.example.com/Project/Tasks/edit``

    Bug: this command should support ``%s`` for specifying the full tasks.txt
    pathname, but it doesn't.

show_office_hours
    whether to show "At office today: NN hours, NN minutes" in the main window

    Example: ``show_office_hours = True``

show_tray_icon
    whether to show a notification icon

    Example: ``show_tray_icon = True``


prefer_app_indicator
    what kind of tray icon do you prefer?

    GTimeLog supports two kinds:

    - Unity application indicator
    - a standard Gtk+ status icon

    Support for each is conditional on the availability of installed libraries.

    Example::

        # prefer Unity application indicators, then fall back to the Gtk+
        # status icon.
        prefer_app_indicator = True

    Example::

        # prefer the Gtk+ status icon, then fall back to Unity app indicator.
        prefer_app_indicator = False

start_in_tray
    whether GTimeLog should start minimized

    This can also be achieved by running ``gtimelog --tray``, so the option is
    of little use.

    This option is ignored if GTimeLog is not using a tray icon (because
    ``show_tray_icon`` is set to ``False``, or if you're missing all the
    libraries).

    Example:: ``start_in_tray = False``

report_style
    choose one of the available report styles for weekly and monthly reports

    Example:: ``report_style = plain`` (the default)

    The report looks like this::

        cat1: entry1                              N h N min
        cat1: entry2                              N h N min
        cat2: entry1                              N h N min

        Total work done this week: N hours N min

        By category:

        cat1: N hours N min
        cat2: N hours N min

    Example:: ``report_style = categorized``

    The report looks like this::

        category 1:
          entry1                                      MM
          entry2                                   HH:MM
        ------------------------------------------------
                                                   HH:MM
        category 2:
          entry1                                      MM
          entry2                                   HH:MM
        ------------------------------------------------
                                                   HH:MM

        Total work done this week: HH:MM

        Categories by time spent:

        category 1       HH:MM
        category 2       HH:MM


EXAMPLE
=======

Example of ``~/.config/gtimelog/gtimelogrc``::

    [gtimelog]

    # Be sure to change these if you want to email the reports somewhere
    name = Anonymous
    list-email = activity@example.com

    # Don't want email?  Just look at reports in a text editor
    mailer = gedit %s

    # Set a goal for 7 hours and 30 minutes of work per day
    hours = 7.5

    # I'll never stay up working this late
    virtual_midnight = 06:00

    # Disable the tray icon
    show_tray_icon = no

    # Hide the Tasks pane on startup
    show_tasks = no


BUGS
====

The config file should not be necessary.  GTimeLog should figure out the
right programs by looking at your desktop preferences; it should remember
the view options from a previous invocation; and it should have a GUI way
for specifying things such as your name or the report mailing list.


FILES
=====

| **~/.gtimelog/gtimelogrc**
| **~/.config/gtimelog/gtimelogrc**

    Configuration file.

    GTimeLog determines the location for the config file as follows:

    1. If the environment variable ``GTIMELOG_HOME`` is set, use
       ``$GTIMELOG_HOME/gtimelogrc``.

    2. If ``~/.gtimelog/`` exists, use ``~/.gtimelog/gtimelogrc``.

    3. If the environment variable ``XDG_CONFIG_HOME`` is set, use
       ``$XDG_CONFIG_HOME/gtimelog/gtimelogrc``.

    4. Use ``~/.config/gtimelog/gtimelogrc``.


SEE ALSO
========

**gtimelog**\ (1)
