Changelog
---------

0.10.3 (2016-10-07)
~~~~~~~~~~~~~~~~~~~

- Make it work (again) when the AppIndicator bindings are not available.


0.10.2 (2016-10-03)
~~~~~~~~~~~~~~~~~~~

* Fix misleading name produced by ``--sample-config`` (GH: #94) when using
  Python 3.


0.10.1 (2016-09-22)
~~~~~~~~~~~~~~~~~~~

* Fix error on Python 3 when using ``task_list_url`` (GH: #92).

* Fix some PyGIWarnings about unspecified versions on startup.


0.10.0 (2015-09-29)
~~~~~~~~~~~~~~~~~~~

* Use Tango colors in the main text buffer (GH: #13).

* Allow tagging entries (GH: #19)

  - The syntax is ``category: text -- tag1 tag2``
  - Per-tag summaries show up in reports

* Use GtkApplication instead of own DBus server for enforcing single-instance.

  - Drop --replace, --ignore-dbus command-line options because of this.
  - Require glib and gio to be version 2.40 or newer for sane
    GtkApplication-based command line parsing
    (check with ``pkg-config --modversion glib-2.0 gio-2.0``).

* Remove obsolete code:

  - Drop support for Python 2.6 (PyGObject dropped support for it long ago).
  - Drop PyGtk/Gtk+ 2 support code (it didn't work since 0.9.1 anyway).
  - Drop EggTrayIcon support (it was for Gtk+ 2 only anyway).
  - Drop the --prefer-pygtk command-line option.

* Disable tray icon by default for new users (existing gtimelogrc files will be
  untouched).

* Improve tray icon selection logic for best contrast (GH: #29).


0.9.3 (2015-09-29)
~~~~~~~~~~~~~~~~~~

* Adding new entries didn't update total weekly numbers (GH: #28).


0.9.2 (2014-09-28)
~~~~~~~~~~~~~~~~~~
* Note that Gtk+ 2.x is no longer supported (this regressed somewhere between
  0.9.0 and 0.9.1, but I didn't notice because I have no access to a system
  that has Gtk+ 2.x).
* Fix setup.py to work on Python 3 when your locale is not UTF-8 (LP: #1263772).
* Fix two Gtk-CRITICAL warnings on startup (GH: #14).
* Fix Unicode warning when adding entries (GH: #20).
* Speed up entry addition (GH: #21).
* Fix Unicode error when navigating history with PageUp/PageDown (GH: #22).
* Update current task time when autoreloading (GH: #23).
* Fix 'LocaleError: unknown encoding:' on Mac OS X (GH: #25).
* Fix 'TypeError: unorderable types: NoneType() < str()' in summary view
  on Python 3 (GH: #26).


0.9.1 (2013-12-23)
~~~~~~~~~~~~~~~~~~
* Manual pages for gtimelog(1) and gtimelogrc(5).


0.9.0 (2013-12-04)
~~~~~~~~~~~~~~~~~~
* New custom date range report by Rohan Mitchell.
* Moved to GitHub.
* HACKING.txt renamed to CONTRIBUTING.rst.
* Tests no longer require PyGTK/PyGObject.
* Add back Python 2.6 support (not 100% guaranteed, I don't have
  PyGObject for 2.6).
* Add Python 3.3 support.


0.8.1 (2013-02-10)
~~~~~~~~~~~~~~~~~~
* Fix strftime problem on Windows (LP: #1096489).
* Fix gtimelog.desktop validation (LP: #1051226).
* Use gtimelog icon instead of gnome-week.png.
* Use XDG Base Directory Specification for config and data files
  (~/.config/gtimelog and ~/.local/share/gtimelog).  There's no automatic
  migration: if ~/.gtimelog exists, it will continue to be used.
* Fix Unicode errors when user's name is non-ASCII (LP: #1117109).
* Dropped Python 2.6 support (by accident).


0.8.0 (2012-08-24)
~~~~~~~~~~~~~~~~~~
* History browsing (LP: #220778).
* New setting to hide the tasks pane on startup (LP: #767096).
* Reload timelog.txt automatically when it changes (LP: #220775).
* Fix segfault on startup (LP: #1016212).
* Summary view (Alt-3) that shows total work in each category.
* Fix popup menu on the task pane (LP: #1040031).
* New command-line option: --prefer-pygtk.  Only useful for testing against the
  deprecated PyGtk bindings instead of the modern pygobject-introspection.
* New command-line option: --quit.
* Fix popup menu of the tray icon (LP: #1039977).
* Fix crash on exit when using Gtk+ 2 (LP: #1040088).
* New command-line option: --debug.
* New command-line option: --version.


0.7.1 (2012-02-01)
~~~~~~~~~~~~~~~~~~
* Fix reporting problems with non-ASCII characters when using
  gobject-introspection (LP: #785578).
* Fix ^C not exiting the app when using gobject-introspection.
* Implement panel icon color autodetection logic that was missing in the
  gobject-introspection case (LP: #924390).
* New command-line option: --help.
* New command-line option: --replace.  Requires that the running version
  support the new DBus method 'Quit', which was also added in this version.
* Messages printed to stdout are prefixed by "gtimelog" (GUI app output often
  ends up in ~/.xsession-errors, it's polite to identify yourself when writing
  there).
* DBus errors do not pass silently.


0.7.0 (2011-09-21)
~~~~~~~~~~~~~~~~~~
* Use gobject-introspection by default, using pygtk only as a fallback.  This
  will require a newer gir1.2-pango-1.0 than what's in Ubuntu Oneiric
  (LP: #855076) and still suffers from key presses being ignored
  (LP: #849732).  Unset the environment variable UBUNTU_MENUPROXY to work
  around the latter bug.
* Rework the gi/pygtk imports so that only the minimum is wrapped in a
  try-except.
* Use /usr/bin/env python in #! line, though this should be hard-coded to the
  installed version of Python in the Debian package.
* Other code cleanup (e.g. use new-style classes via __metaclass__, remove
  ancient workaround for missing `set` built-in).


0.6.1 (2011-09-20)
~~~~~~~~~~~~~~~~~~
* Fix two crashes when using GI.  Given by Martin Pitt.


0.6.0 (2011-08-23)
~~~~~~~~~~~~~~~~~~
* Ctrl-Q now quits.  (LP: #750092)
* Fixed UnboundLocalError.  (LP: #778285)  Given by Jeroen Langeveld.
* Ported from PyGTK to GI. This supports GTK 2 and GTK 3 with GI now, but still
  works with PyGTK.
  Contributed by Martin Pitt <martin.pitt@ubuntu.com>.

  Packager's note: If you want to use GI, you need to change the package's
  dependencies from pygtk to the package that provides the GTK and Pango
  typelibs (e. g. gir1.2-gtk-2.0 and gir1.2-pango-1.0 on Debian/Ubuntu). It
  also requires pygobject >= 2.27.1.

* Hide the main window on Esc.  Fixes LP: #716257.
  Contributed by Vladislav Naumov (https://launchpad.net/~vnaum).


0.5.0 (2011-01-28)
~~~~~~~~~~~~~~~~~~
* Switched from Glade to GtkBuilder.  This fixes those strange theme problems
  GTimeLog had with Ubuntu's Radiance and especially Ambiance. (LP: #644393)

  Packagers note: src/gtimelog/gtimelog.glade is gone, it was replaced by
  src/gtimelog/gtimelog.ui.  It needs to be installed into
  /usr/share/gtimelog/.

* GTimeLog now supports Ubuntu's application indicators.  There's a new
  configuration option, ``prefer_app_indicator``, defaulting to true.
  Fixes LP: #523461.
* GTimeLog tries to detect your theme color and make the tray icon dark or
  bright, for good contrast.  This is a hack that doesn't work reliably, but
  is better than nothing.  Fixes LP: #700428.

  Packagers note: there's a new icon file,
  src/gtimelog/gtimelog-small-bright.png.  It needs to be installed into
  /usr/share/gtimelog/.

* Made GTimeLog a single instance application.  Requires python-dbus.
  The following command line options are supported::

    gtimelog --ignore-dbus
        Always launch a new application instance, do not start the DBus
        service.

    gtimelog --toggle
        If GtimeLog already running, show or hide the GTimeLog window,
        otherwise launch a new application instance.

    gtimelog
        If GtimeLog already running, bring the GTimeLog window to the front,
        otherwise launch a new application instance.

  Contributed by Bruce van der Kooij (https://launchpad.net/~brucevdk),
  Fixes LP: #356495.

* New option: start_in_tray.  Defaults to false.  Contributed by Bruce van der
  Kooij (https://launchpad.net/~brucevdk), as part of his patch for LP:
  #356495.
* New command-line option: --tray.  Makes GTimeLog start minimized, or exit
  without doing anything if it's already running.
* Added some documentation for contributors: HACKING.txt.
* Daily reports include totals by category.  Contributed by Laurynas SpeiÄys
  <laurynas@pov.lt>.
* The tasks pane can be toggled by pressing F9 and has a close button.
* Alternative weekly and monthly report style, can be chosen by adding
  ``report_style = categorized`` to ~/.gtimelog/gtimelogrc.
  Contributed by Laurynas SpeiÄys <laurynas@pov.lt>.
* Bugfix: always preserve the order of entries, even when they have the same
  timestamp (LP: #708825).


0.4.0 (2010-09-03)
~~~~~~~~~~~~~~~~~~
* Added configuration variable 'chronological' to control initial view of
  either Chronological (True) or Grouped (False).  Contributed by Barry Warsaw
  <barry@python.org> (LP: #628876)
* Recognize $GTIMELOG_HOME environment variable to use something other than
  ~/.gtimelog as the configuration directory.  Contributed by Barry Warsaw
  <barry@python.org> (LP: #628873)
* Changed application name to 'GTimeLog Time Tracker' in the desktop file
  (Debian #595280)


0.3.2 (2010-07-22)
~~~~~~~~~~~~~~~~~~
* Double-clicking a category in task list tries hard to focus the input box
  (fixes: https://bugs.launchpad.net/gtimelog/+bug/608734).
* Change default mailer to quote the command passed to x-terminal-emulator -e;
  this makes it work with Terminator (also tested with xterm and
  gnome-terminal).  Fixes https://bugs.launchpad.net/gtimelog/+bug/592552.

  Note: if you've used gtimelog before, you'll have to manually edit
  ~/.gtimelog/gtimelogrc and change the mailer line from

    mailer = x-terminal-emulator -e mutt -H %s

  to

    mailer = x-terminal-emulator -e "mutt -H %s"

* Use xdg-open by default for editing timelog.txt and opening spreadsheets.
  Fixes https://bugs.launchpad.net/gtimelog/+bug/592560.

  Note: if you've used gtimelog before, you'll have to manually edit
  ~/.gtimelog/gtimelogrc and change

    editor = gvim
    spreadhsheet = oocalc %s

  to

    editor = xdg-open
    spreadsheet = xdg-open %s


0.3.1 (2009-12-18)
~~~~~~~~~~~~~~~~~~
* Fixed broken sdist (by adding MANIFEST.in, since setuptools doesn't
  understand bzr by default).
* Added Makefile for convenience (make distcheck, make release).


0.3 (2009-12-17)
~~~~~~~~~~~~~~~~
* Fix DeprecationWarning: the sets module is deprecated.
* Use gtk.StatusIcon if egg.trayicon is not available
  (https://bugs.launchpad.net/gtimelog/+bug/209798).
* Option to select between old-style and new-style the tray icons:
  'prefer_old_tray_icon' in ~/.gtimelog/gtimelogrc
* Option to disable the tray icon altogether by adding 'show_tray_icon = no' to
  ~/.gtimelog/gtimelogrc (https://bugs.launchpad.net/gtimelog/+bug/255618).
* Handle directory names with spaces
  (https://bugs.launchpad.net/gtimelog/+bug/328118).
* Show version number in the About dialog
  (https://bugs.launchpad.net/gtimelog/+bug/308750).

Packagers take note: the main module was renamed from gtimelog.gtimelog to
gtimelog.main.  If you have wrapper scripts that used to import 'main'
from gtimelog.gtimelog, you'll have to change them.


0.2.5
~~~~~
* Don't open a console window on Windows.
* Moved the primary GTimeLog source repository to Bazaar hosted on Launchpad.


0.2.4
~~~~~
* Show time spent at the office
  (https://bugs.launchpad.net/gtimelog/+bug/238515).
* Closing the main window minimizes GTimeLog to the system tray
  (https://bugs.launchpad.net/gtimelog/+bug/239271)
* Ability to time-offset new log item
  (https://bugs.launchpad.net/bugs/291356)


0.2.3
~~~~~
* Fix duplicates in the completion popup after you reload the log file
  (https://bugs.launchpad.net/gtimelog/+bug/238505).
* Change status to Beta in setup.py -- while I still consider it to be
  less polished than it should, there are people who find it useful already.


0.2.2
~~~~~
* Tweak setup.py to get a sane page at http://pypi.python.org/pypi/gtimelog/


0.2.1
~~~~~
* Entries with `***` are skipped from reports (bug 209750)
* Help -> Online Documentation opens a browser with some help (bug 209754)
* View -> Tasks allows you to hide the Tasks pane (bug 220773)


0.2.0
~~~~~
* Reorganize the source tree properly.
* Bump intermediate revision number to celebrate.


0.0.85
~~~~~~
* First setuptools-based release (`easy_install gtimelog` now works).


Changes in older versions
~~~~~~~~~~~~~~~~~~~~~~~~~

You'll have to dig through Git logs to discover those, if you're really
that interested: https://github.com/gtimelog/gtimelog/commits
