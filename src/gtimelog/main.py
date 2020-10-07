"""An application for keeping track of your time."""
import gettext
import locale
import logging
import os
import signal
import sys
from gettext import gettext as _

from gtimelog import DEBUG
from gtimelog.core.utils import mark_time
from gtimelog.paths import LOCALE_DIR


def require_version(namespace, version):
    try:
        import gi
        gi.require_version(namespace, version)
    except ValueError:
        deb_package = "gir1.2-{namespace}-{version}".format(
            namespace=namespace.lower(), version=version)
        sys.exit("""Typelib files for {namespace}-{version} are not available.

If you're on Ubuntu or another Debian-like distribution, please install
them with

    sudo apt install {deb_package}
""".format(namespace=namespace, version=version, deb_package=deb_package))


require_version('Gtk', '3.0')
require_version('Soup', '2.4')
require_version('Secret', '1')

mark_time("in script")

if DEBUG:
    os.environ['G_ENABLE_DIAGNOSTIC'] = '1'

root_logger = logging.getLogger()
root_logger.addHandler(logging.StreamHandler())
root_logger.setLevel(logging.DEBUG if DEBUG else logging.INFO)

# Due to gi susceptibility, we load components at last
from gtimelog.ui.components.application import Application


def main():
    mark_time("in main()")

    log = root_logger.getChild('gtimelog')
    # Tell Python's gettext.gettext() to use our translations
    gettext.bindtextdomain('gtimelog', LOCALE_DIR)
    gettext.textdomain('gtimelog')

    # Tell GTK+ to use out translations
    if hasattr(locale, 'bindtextdomain'):
        locale.bindtextdomain('gtimelog', LOCALE_DIR)
        locale.textdomain('gtimelog')
    else:  # pragma: nocover
        # https://github.com/gtimelog/gtimelog/issues/95#issuecomment-252299266
        # locale.bindtextdomain is missing on Windows!
        log.error(_("Unable to configure translations: no locale.bindtextdomain()"))

    # Make ^C terminate the process
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # Run the app
    app = Application()
    mark_time("app created")
    try:
        sys.exit(app.run(sys.argv))
    finally:
        mark_time("exiting")


if __name__ == '__main__':
    main()
