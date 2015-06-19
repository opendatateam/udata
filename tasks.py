# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import json
import os
import re
import itertools


from glob import iglob
from os.path import join, abspath, dirname, exists

from invoke import run, task

ROOT = abspath(join(dirname(__file__)))
I18N_DOMAIN = 'udata-admin'


def green(text):
    return '\033[1;32m{0}\033[0;m'.format(text)


def red(text):
    return '\033[1;31m{0}\033[0;m'.format(text)


def cyan(text):
    return '\033[1;36m{0}\033[0;m'.format(text)


def lrun(command, *args, **kwargs):
    run('cd {0} && {1}'.format(ROOT, command), *args, **kwargs)


def nrun(command, *args, **kwargs):
    lrun('node_modules/.bin/{0}'.format(command), *args, **kwargs)


@task
def clean(bower=False, node=False):
    '''Cleanup all build artifacts'''
    patterns = [
        'build', 'dist', 'cover', 'docs/_build', 'udata_admin/static',
        '**/*.pyc', '**/*.mo', '*.egg-info', '.tox'
    ]
    if bower:
        patterns.append('bower_components')
    if node:
        patterns.append('node_modules')
    for pattern in patterns:
        print('Removing {0}'.format(red(pattern)))
        lrun('rm -rf {0}'.format(pattern))


@task
def test():
    '''Run tests suite'''
    print(cyan('Running tests suites'))
    lrun('nosetests --rednose --force-color', pty=True)
    lrun('karma start --browsers=PhantomJS --single-run', pty=True)


@task
def karma():
    '''Continuous Karma test'''
    lrun('karma start --browsers=PhantomJS', pty=True)


@task
def cover():
    '''Run tests suite with coverage'''
    lrun('nosetests --rednose --force-color \
        --with-coverage --cover-html --cover-package=udata_me', pty=True)


@task
def qa():
    '''Run a quality report'''
    print(cyan('Running Flake8 report'))
    run('flake8 {0}/udata_me'.format(ROOT))
    print(green('OK'))
    print(cyan('Running JSHint report'))
    nrun('jshint js --extra-ext=.vue --extract=auto')
    print(green('OK'))


@task
def i18n():
    '''
    Extract translatables strings
    '''
    print(cyan('Extracting Python strings'))
    lrun('python setup.py extract_messages')
    lrun('python setup.py update_catalog')

    print(cyan('Extracting Javascript strings'))
    catalog = {}
    catalog_filename = join(ROOT, 'locales', '{}.en.json'.format(I18N_DOMAIN))
    if exists(catalog_filename):
        with open(catalog_filename) as f:
            catalog = json.load(f)

    globs = '*.js', '*.vue'
    regexps = [
        re.compile(r'(?:|\.|\s|\{)_\(\s*(?:"|\')(.*?)(?:"|\')\s*(?:\)|,)'),
        # re.compile(r'this\._\(\s*(?:"|\')(.*?)(?:"|\')\s*\)'),
        re.compile(r'v-i18n="(.*?)"'),
        re.compile(r'"\{\{\{?\s*\'(.*?)\'\s*\|\s*i18n\}\}\}?"'),
    ]

    for directory, _, _ in os.walk(join(ROOT, 'js')):
        glob_patterns = (iglob(join(directory, g)) for g in globs)
        for filename in itertools.chain(*glob_patterns):
            print('Extracting messages from {0}'.format(green(filename)))
            content = open(filename, 'r').read()
            for regexp in regexps:
                for match in regexp.finditer(content):
                    key = match.group(1)
                    if not key in catalog:
                        catalog[key] = key

    with open(catalog_filename, 'wb') as f:
        json.dump(catalog, f, sort_keys=True, indent=4, ensure_ascii=False)


@task
def watch():
    lrun('webpack -d -c --progress --watch', pty=True)


@task
def update():
    print('Installing required dependencies')
    lrun('npm install')
    print('Fetching last translations')
    lrun('tx pull')


@task
def build():
    print(cyan('Building static assets'))
    lrun('webpack -c --progress -p --config webpack.config.prod.js', pty=True)
    print(cyan('Compiling translations'))
    lrun('python setup.py compile_catalog')


@task(build)
def dist():
    '''Package for distribution'''
    print(cyan('Building a distribuable package'))
    lrun('python setup.py bdist_wheel', pty=True)


@task(test, qa, dist, default=True)
def all():
    pass
