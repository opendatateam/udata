#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import re

from os.path import join, dirname

from setuptools import setup, find_packages

RE_REQUIREMENT = re.compile(r'^\s*-r\s*(?P<filename>.*)$')

PYPI_CLEANDOC_FILTERS = (
    # Remove badges lines
    (r'\n.*travis-.*', ''),
    (r'\n.*requires-.*', ''),
    (r'\n.*david-dm.*', ''),
    (r'\n.*gitter-.*', ''),
    (r'\n.*coveralls-.*', ''),
    # Transform links
    (r'\[(.+)\]\[(.+)\]', '`\g<1> <\g<2>_>`_'),
    (r'\[(.+)\]:\s*(.+)\s*', '.. _\g<1>: \g<2>'),
    (r'\[(.+)\]\((.+)\)', '`\g<1> <\g<2>>`_'),
)

ROOT = dirname(__file__)


def clean_doc(filename):
    """Load markdown file and sanitize it for PyPI restructuredtext.

    Remove unsupported github tags:
     - various badges

    Transform markdown links into restructuredtext
    """
    content = open(join(ROOT, filename)).read()
    for regex, replacement in PYPI_CLEANDOC_FILTERS:
        content = re.sub(regex, replacement, content)
    return content


def pip(filename):
    """Parse pip reqs file and transform it to setuptools requirements."""
    requirements = []
    for line in open(join(ROOT, 'requirements', filename)):
        line = line.strip()
        if not line or '://' in line:
            continue
        match = RE_REQUIREMENT.match(line)
        if match:
            requirements.extend(pip(match.group('filename')))
        else:
            requirements.append(line)
    return requirements


def dependency_links(filename):
    return [line.strip()
            for line in open(join(ROOT, 'requirements', filename))
            if '://' in line]

install_requires = pip('install.pip')
tests_require = pip('test.pip')
readme_md = clean_doc('README.md')

setup(
    name='udata',
    version=__import__('udata').__version__,
    description=__import__('udata').__description__,
    long_description=readme_md,
    url='https://github.com/etalab/udata',
    download_url='http://pypi.python.org/pypi/udata',
    author='Axel Haustant',
    author_email='axel@data.gouv.fr',
    packages=find_packages(),
    include_package_data=True,
    install_requires=install_requires,
    dependency_links=dependency_links('install.pip'),
    tests_require=tests_require,
    extras_require={
        'test': tests_require,
        'sentry': ['raven[flask]>=5.3.0'],
    },
    entry_points={
        'console_scripts': [
            'udata = udata.commands:console_script',
        ]
    },
    license='GNU AGPLv3+',
    # use_2to3=True,
    keywords='',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Programming Language :: Python',
        'Environment :: Web Environment',
        'Operating System :: OS Independent',
        'Intended Audience :: Developers',
        'Topic :: System :: Software Distribution',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Topic :: Software Development :: Libraries :: Python Modules',
        ('License :: OSI Approved :: GNU Affero General Public License v3'
         ' or later (AGPLv3+)'),
    ],
)
