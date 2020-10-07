"""
Misc utils
"""

import sys

import gi


def require_version(namespace, version):
    try:
        gi.require_version(namespace, version)
    except ValueError:
        deb_package = "gir1.2-{namespace}-{version}".format(
            namespace=namespace.lower(), version=version)
        sys.exit("""Typelib files for {namespace}-{version} are not available.

If you're on Ubuntu or another Debian-like distribution, please install
them with

    sudo apt install {deb_package}
""".format(namespace=namespace, version=version, deb_package=deb_package))
