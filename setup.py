#!/usr/bin/env python

import io
import os
import re

from setuptools import setup, find_packages

RE_REQUIREMENT = re.compile(r'^\s*-r\s*(?P<filename>.*)$')
RE_BADGE = re.compile(r'^\[\!\[(?P<text>[^\]]+)\]\[(?P<badge>[^\]]+)\]\]\[(?P<target>[^\]]+)\]$', re.M)

BADGES_TO_KEEP = ['gitter-badge', 'readthedocs-badge']


def md(filename):
    '''
    Load .md (markdown) file and sanitize it for PyPI.
    Remove unsupported github tags:
     - code-block directive
     - travis ci build badges
    '''
    content = io.open(filename).read()

    for match in RE_BADGE.finditer(content):
        if match.group('badge') not in BADGES_TO_KEEP:
            content = content.replace(match.group(0), '')
    return content


long_description = '\n'.join((
    md('README.md'),
    md('CHANGELOG.md'),
    ''
))


def pip(filename):
    """Parse pip reqs file and transform it to setuptools requirements."""
    requirements = []
    for line in open(os.path.join('requirements', filename)):
        line = line.strip()
        if not line or '://' in line or line.startswith('#'):
            continue
        match = RE_REQUIREMENT.match(line)
        if match:
            requirements.extend(pip(match.group('filename')))
        else:
            requirements.append(line)
    return requirements


install_requires = pip('install.pip')
tests_require = pip('test.pip')

setup(
    name='udata',
    version=__import__('udata').__version__,
    description=__import__('udata').__description__,
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/opendatateam/udata',
    author='Opendata Team',
    author_email='opendatateam@data.gouv.fr',
    packages=find_packages(),
    include_package_data=True,
    python_requires='>=3.7',
    install_requires=install_requires,
    setup_requires=['setuptools>=38.6.0'],
    tests_require=tests_require,
    extras_require={
        'test': tests_require,
        'sentry': ['raven[flask]>=6.1.0'],
    },
    entry_points={
        'console_scripts': [
            'udata = udata.commands:cli',
        ],
        'udata.themes': [
            'default = udata.theme.default',
        ],
        'udata.harvesters': [
            'dcat = udata.harvest.backends.dcat:DcatBackend',
        ],
        'udata.avatars': [
            'internal = udata.features.identicon.backends:internal',
            'adorable = udata.features.identicon.backends:adorable',
            'robohash = udata.features.identicon.backends:robohash',
        ],
        'pytest11': [
            'udata = udata.tests.plugin',
        ],
    },
    license='GNU AGPLv3+',
    keywords='udata opendata portal data',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Programming Language :: Python',
        'Environment :: Web Environment',
        'Operating System :: OS Independent',
        'Intended Audience :: Developers',
        'Topic :: System :: Software Distribution',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Topic :: Software Development :: Libraries :: Python Modules',
        ('License :: OSI Approved :: GNU Affero General Public License v3'
         ' or later (AGPLv3+)'),
    ],
)
