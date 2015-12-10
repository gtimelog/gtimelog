#!/usr/bin/env python
import os
import re
import io
from setuptools import setup

here = os.path.dirname(__file__)


def read(filename):
    with io.open(os.path.join(here, filename), 'r', encoding='utf-8') as f:
        return f.read()


metadata = dict(
    (k, eval(v)) for k, v in
    re.findall('^(__version__|__author__|__url__|__licence__) = (.*)$',
               read('src/gtimelog/__init__.py'), flags=re.MULTILINE)
)

version = metadata['__version__']

changes = read('NEWS.rst').split('\n\n\n')
changes_in_latest_versions = '\n\n\n'.join(changes[:3])
older_changes = '''
Older versions
~~~~~~~~~~~~~~

See the `full changelog`_.

.. _full changelog: https://github.com/gtimelog/gtimelog/blob/master/NEWS.rst
'''

short_description = 'A Gtk+ time tracking application'
long_description = (
    read('README.rst') +
    '\n\n' +
    changes_in_latest_versions +
    '\n\n' +
    older_changes
)

setup(
    name='gtimelog',
    version=version,
    author='Marius Gedminas',
    author_email='marius@gedmin.as',
    url='http://mg.pov.lt/gtimelog/',
    description=short_description,
    long_description=long_description,
    license='GPL',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: X11 Applications :: GTK',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Topic :: Office/Business',
    ],

    packages=['gtimelog'],
    package_dir={'': 'src'},
    package_data={'gtimelog': ['*.ui', '*.png']},
    test_suite='gtimelog.tests',
    tests_require=['freezegun', 'mock'],
    zip_safe=False,
    entry_points="""
    [gui_scripts]
    gtimelog = gtimelog.main:main
    """,
# This is true, but pointless, because PyGObject cannot be installed via
# setuptools/distutils
#   install_requires=['PyGObject'],
)
