#!/usr/bin/env python
import ast
import os
import re
import sys

from setuptools import find_packages, setup


here = os.path.dirname(__file__)


def read(filename):
    with open(os.path.join(here, filename), encoding='utf-8') as f:
        return f.read()


metadata = {
    k: ast.literal_eval(v)
    for k, v in re.findall(
        '^(__version__|__author__|__url__|__licence__) = (.*)$',
        read('src/gtimelog/__init__.py'),
        flags=re.MULTILINE,
    )
}

version = metadata['__version__']

changes = read('CHANGES.rst').split('\n\n\n')
changes_in_latest_versions = '\n\n\n'.join(changes[:3])
older_changes = '''
Older versions
~~~~~~~~~~~~~~

See the `full changelog`_.

.. _full changelog: https://github.com/gtimelog/gtimelog/blob/master/CHANGES.rst
'''

short_description = 'A Gtk+ time tracking application'
long_description = ''.join([
    read('README.rst'),
    '\n\n',
    changes_in_latest_versions,
    '\n\n',
    older_changes,
])

tests_require = ['freezegun']
if sys.version_info < (3, 6, 0):
    sys.exit("Python 3.6 is the minimum required version")

setup(
    name='gtimelog',
    version=version,
    author='Marius Gedminas',
    author_email='marius@gedmin.as',
    url='https://gtimelog.org/',
    description=short_description,
    long_description=long_description,
    long_description_content_type='text/x-rst',
    license='GPL',
    keywords='time log logging timesheets gnome gtk',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: X11 Applications :: GTK',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Office/Business',
    ],
    python_requires='>= 3.7',

    packages=find_packages('src'),
    package_dir={'': 'src'},
    include_package_data=True,
    package_data={'': ['locale/*/LC_MESSAGES/gtimelog.mo']},
    test_suite='gtimelog.tests',
    tests_require=tests_require,
    extras_require={
        'test': [
            'freezegun',
        ],
    },
    zip_safe=False,
    entry_points="""
    [gui_scripts]
    gtimelog = gtimelog.main:main
    """,
    install_requires=['PyGObject'],
)
