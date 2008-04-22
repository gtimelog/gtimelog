#!/usr/bin/env python
from setuptools import setup

setup(
    name='gtimelog',
    version='0.2.0',
    author='Marius Gedminas',
    author_email='marius@gedmin.as',
    url='http://mg.pov.lt/gtimelog/',
    description='A Gtk+ time tracking application',
    license='GPL',
    classifiers = [
        'Development Status :: 3 - Alpha',
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
    [console_scripts]
    gtimelog = gtimelog.gtimelog:main
    """,
# This is true, but pointless, because easy_install PyGTK chokes and dies
#   install_requires=['PyGTK'],
)
