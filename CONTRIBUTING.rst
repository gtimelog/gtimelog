Contributing to GTimeLog
========================

Contributions are welcome, and not just code patches.  I'd love to see

* user interface design sketches
* icons
* documentation
* translations
* installers for Mac OS X and Windows


Bugs
----

Please `use GitHub <https://github.com/gtimelog/gtimelog/issues>`_ to
report bugs or feature requests.

We also have an older issue tracker on `Launchpad
<https://bugs.launchpad.net/gtimelog/>`_.  Some bugs haven't been moved
over to GitHub yet.

You may also contact Marius Gedminas <marius@gedmin.as> or Barry Warsaw
<barry@python.org> by email.


Source code
-----------

It's on GitHub: https://github.com/gtimelog/gtimelog

Get the latest version with ::

    $ git clone https://github.com/gtimelog/gtimelog

Run it without installing ::

    $ cd gtimelog
    $ make
    $ ./gtimelog


Tests
-----

Run the test suite with ::

    $ ./runtests

or, to test against all supported Python versions ::

    $ pip install tox
    $ tox
