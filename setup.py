#!/usr/bin/env python

import os
import io
import re

from setuptools import setup, find_packages

RE_BADGE = re.compile(r'^\[\!\[(?P<text>.*?)\]\[(?P<badge>.*?)\]\]\[(?P<target>.*?)\]$', re.M)

BADGES_TO_KEEP = ['gitter-badge']


def md(filename):
    '''
    Load .md (markdown) file and sanitize it for PyPI.
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
    return open(os.path.join('requirements', filename)).readlines()


setup(
    name='udata-gouvfr',
    version=__import__('udata_gouvfr').__version__,
    description=__import__('udata_gouvfr').__description__,
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/etalab/udata-gouvfr',
    author='Etalab',
    author_email='pypi@data.gouv.fr',
    packages=find_packages(),
    include_package_data=True,
    python_requires='>=3.7',
    install_requires=pip('install.pip'),
    setup_requires=['setuptools>=38.6.0'],
    tests_require=pip('test.pip'),
    extras_require={
        'test': pip('test.pip'),
    },
    entry_points={
        'udata.themes': [
            'gouvfr = udata_gouvfr.theme',
        ],
        'udata.metrics': [
            'gouvfr = udata_gouvfr.metrics',
        ],
        'udata.models': [
            'gouvfr = udata_gouvfr.models',
        ],
        'udata.views': [
            'gouvfr = udata_gouvfr.views',
        ],
        'udata.harvesters': [
            'maaf = udata_gouvfr.harvesters.maaf:MaafBackend',
        ]
    },
    license='LGPL',
    zip_safe=False,
    keywords='udata opendata portal etalab',
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Programming Language :: Python",
        "Environment :: Web Environment",
        "Operating System :: OS Independent",
        "Intended Audience :: Developers",
        "Topic :: System :: Software Distribution",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Topic :: Software Development :: Libraries :: Python Modules",
        ('License :: OSI Approved :: GNU Library or Lesser General Public '
         'License (LGPL)'),
    ],
)
