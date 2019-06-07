GTimeLog
========

GTimeLog is a simple app for keeping track of time.

.. image:: https://travis-ci.org/gtimelog/gtimelog.svg?branch=master
   :target: https://travis-ci.org/gtimelog/gtimelog
   :alt: build status

.. image:: https://ci.appveyor.com/api/projects/status/github/gtimelog/gtimelog?branch=master&svg=true
   :target: https://ci.appveyor.com/project/mgedmin/gtimelog
   :alt: build status (on Windows)

.. image:: https://coveralls.io/repos/gtimelog/gtimelog/badge.svg?branch=master
   :target: https://coveralls.io/r/gtimelog/gtimelog?branch=master
   :alt: test coverage

.. contents::

.. image:: https://raw.github.com/gtimelog/gtimelog/master/docs/gtimelog.png
   :alt: screenshot


Installing
----------

GTimeLog is packaged for Debian and Ubuntu::

  sudo apt-get install gtimelog

For Ubuntu, a newer version can usually be found in the PPA:

  https://launchpad.net/~gtimelog-dev/+archive/ppa

You can fetch the latest released version from PyPI ::

  $ pip install gtimelog
  $ gtimelog

You can run it from a source checkout without an explicit installation step::

  $ git clone https://github.com/gtimelog/gtimelog
  $ cd gtimelog
  $ make
  $ ./gtimelog

System requirements:

- Python (2.7 or 3.3+)
- PyGObject
- gobject-introspection type libraries for GTK+, Pango
- GTK+ 3.10 or newer (3.14 or newer for best results)


Documentation
-------------

This is work in progress:

- `docs/index.rst`_ contains an overview
- `docs/formats.rst`_ describes the file formats

.. _docs/index.rst: https://github.com/gtimelog/gtimelog/blob/master/docs/index.rst
.. _docs/formats.rst: https://github.com/gtimelog/gtimelog/blob/master/docs/formats.rst


Resources
---------

Website: https://gtimelog.org

Mailing list: gtimelog@googlegroups.com
(archive at https://groups.google.com/group/gtimelog)

IRC: #gtimelog on irc.freenode.net

Source code: https://github.com/gtimelog/gtimelog

Report bugs at https://github.com/gtimelog/gtimelog/issues

There's an old bugtracker at https://bugs.launchpad.net/gtimelog

I sometimes also browse distribution bugs:

- Ubuntu https://bugs.launchpad.net/ubuntu/+source/gtimelog
- Debian https://bugs.debian.org/gtimelog


Credits
-------

GTimeLog was mainly written by Marius Gedminas <marius@gedmin.as>.

Barry Warsaw <barry@python.org> stepped in as a co-maintainer when
Marius burned out.  Then Barry got busy and Marius recovered.

Many excellent contributors are listed in `CONTRIBUTORS.rst`_

.. _CONTRIBUTORS.rst: https://github.com/gtimelog/gtimelog/blob/master/src/gtimelog/CONTRIBUTORS.rst
