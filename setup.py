#!/usr/bin/env python
import os
import re
from setuptools import setup

here = os.path.dirname(__file__)


def read(filename):
    with open(os.path.join(here, filename)) as f:
        return f.read()


metadata = dict(
    (k, eval(v)) for k, v in
    re.findall('^(__version__|__author__|__url__|__licence__) = (.*)$',
               read('src/gtimelog/__init__.py'), flags=re.MULTILINE)
)

version = metadata['__version__']

changes = read('NEWS.rst').split('\n\n\n')
changes_in_latest_versions = '\n\n\n'.join(changes[:3])

short_description = 'A Gtk+ time tracking application'
long_description = '''
Simple and unintrusive time-tracking application.

There are screenshots at http://mg.pov.lt/gtimelog.

Mailing list: http://groups.google.com/group/gtimelog

Bugs: https://github.com/gtimelog/gtimelog/issues

Source code: https://github.com/gtimelog/gtimelog
'''

setup(
    name='gtimelog',
    version=version,
    author='Marius Gedminas',
    author_email='marius@gedmin.as',
    url='http://mg.pov.lt/gtimelog/',
    description=short_description,
    long_description=long_description + '\n\n' + changes_in_latest_versions,
    license='GPL',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: X11 Applications :: GTK',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Programming Language :: Python :: 2.7',
        # 2.6 might work, but I can't test it
        'Topic :: Office/Business',
    ],

    packages=['gtimelog'],
    package_dir={'gtimelog': 'src/gtimelog'},
    package_data={'gtimelog': ['*.ui', '*.png']},
    test_suite='gtimelog.tests',
    zip_safe=False,
    entry_points="""
    [gui_scripts]
    gtimelog = gtimelog.main:main
    """,
# This is true, but pointless, because PyGObject cannot be installed via
# setuptools/distutils
#   install_requires=['PyGObject'], # or PyGTK
)
