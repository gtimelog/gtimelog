#!/usr/bin/env python
import os
from setuptools import setup

here = os.path.dirname(__file__)

version_file = os.path.join(here, 'src/gtimelog/__init__.py')
d = {}
execfile(version_file, d)
version = d['__version__']

changes_file = os.path.join(here, 'NEWS.txt')
changes = file(changes_file).read().split('\n\n\n')
changes_in_latest_versions = '\n\n\n'.join(changes[:3])

short_description = 'A Gtk+ time tracking application'
long_description = '''
Simple and unintrusive time-tracking application.

There are screenshots at http://mg.pov.lt/gtimelog.

Mailing list: http://groups.google.com/group/gtimelog

Bugs: http://bugs.launchpad.net/gtimelog/

Source code: http://code.launchpad.net/gtimelog/
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
    classifiers = [
        'Development Status :: 4 - Beta',
        'Environment :: X11 Applications :: GTK',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Topic :: Office/Business',
    ],

    packages=['gtimelog'],
    package_dir={'gtimelog': 'src/gtimelog'},
    package_data={'gtimelog': ['*.glade', '*.png']},
    test_suite='gtimelog.test_gtimelog',
    zip_safe=False,
    entry_points="""
    [gui_scripts]
    gtimelog = gtimelog.main:main
    """,
# This is true, but pointless, because easy_install PyGTK chokes and dies
#   install_requires=['PyGTK'],
)
