#!/usr/bin/env python

import os

from setuptools import setup, find_packages


def file_content(filename):
    '''Load file content'''
    with open(filename) as ifile:
        return ifile.read()


def pip(filename):
    """Return path to pip requirements file"""
    return file_content(os.path.join('requirements', filename))


long_description = '\n'.join((
    file_content('README.md'),
    file_content('CHANGELOG.md'),
    ''
))


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
    entry_points={
        'udata.themes': [
            'gouvfr = udata_gouvfr.theme.gouvfr',
        ],
        'udata.models': [
            'gouvfr = udata_gouvfr.models',
        ],
        'udata.front': 'gouvfr = udata_gouvfr.frontend',
        'udata.apis': [
            'gouvfr_oembed = udata_gouvfr.views.oembed',
        ],
        'udata.harvesters': [
            'maaf = udata_gouvfr.harvesters.maaf:MaafBackend',
        ],
        'udata.tasks': [
             'gouvfr = udata_gouvfr.tasks',
        ],
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
