# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import codecs
import itertools
import json
import os
import re

from glob import iglob
from os.path import join, exists
from sys import exit

from invoke import run, task

from tasks_helpers import ROOT, info, header, lrun, nrun, green

I18N_DOMAIN = 'udata'


@task
def clean(bower=False, node=False):
    '''Cleanup all build artifacts'''
    header('Clean all build artifacts')
    patterns = [
        'build', 'dist', 'cover', 'docs/_build',
        '**/*.pyc', '*.egg-info', '.tox'
    ]
    if bower:
        patterns.append('udata/static/bower')
    if node:
        patterns.append('node_modules')
    for pattern in patterns:
        info('Removing {0}'.format(pattern))
        run('cd {0} && rm -rf {1}'.format(ROOT, pattern))


@task
def test():
    '''Run tests suite'''
    header('Run tests suite')
    lrun('nosetests --rednose --force-color udata', pty=True)


@task
def cover():
    '''Run tests suite with coverage'''
    header('Run tests suite with coverage')
    lrun('nosetests --rednose --force-color \
        --with-coverage --cover-html --cover-package=udata', pty=True)


@task
def jstest(hot=False):
    '''Run JS tests suite'''
    header('Run client tests suite')
    cmd = 'webpack-dev-server --config webpack.config.test.js'
    if hot:
        cmd += ' --hot --inline'
    nrun(cmd, pty=True)


@task
def karma():
    '''Continuous Karma test'''
    lrun('karma start --browsers=PhantomJS', pty=True)


@task
def doc():
    '''Build the documentation'''
    header('Building documentation')
    lrun('cd doc && make html', pty=True)


@task
def jsdoc():
    '''Build the JS documentation'''
    header('Build the JS documentation')
    nrun('esdoc -c esdoc.json', pty=True)


@task
def qa():
    '''Run a quality report'''
    header('Performing static analysis')
    info('Python static analysis')
    flake8_results = lrun('flake8 udata', warn=True)
    info('JavaScript static analysis')
    jshint_results = nrun('jshint js --extra-ext=.vue --extract=auto', warn=True)
    if flake8_results.failed or jshint_results.failed:
        exit(flake8_results.return_code or jshint_results.return_code)
    print(green('OK'))


@task
def serve():
    '''Run a development server'''
    lrun('python manage.py serve -d -r', pty=True)


@task
def work(loglevel='info'):
    '''Run a development worker'''
    run('celery -A udata.worker worker --purge --autoreload -l %s' % loglevel, pty=True)


@task
def beat(loglevel='info'):
    '''Run celery beat process'''
    run('celery -A udata.worker beat -l %s' % loglevel)


@task
def i18n():
    '''Extract translatable strings'''
    header('Extract translatable strings')

    info('Extract Python strings')
    lrun('python setup.py extract_messages')
    lrun('python setup.py update_catalog')

    info('Extract JavaScript strings')
    keys = []
    catalog = {}
    catalog_filename = join(ROOT, 'js', 'locales',
                            '{}.en.json'.format(I18N_DOMAIN))
    not_found = {}
    not_found_filename = join(ROOT, 'js', 'locales',
                            '{}.notfound.json'.format(I18N_DOMAIN))
    if exists(catalog_filename):
        with codecs.open(catalog_filename, encoding='utf8') as f:
            catalog = json.load(f)

    globs = '*.js', '*.vue', '*.hbs'
    regexps = [
        re.compile(r'(?:|\.|\s|\{)_\(\s*(?:"|\')(.*?)(?:"|\')\s*(?:\)|,)'),
        # re.compile(r'this\._\(\s*(?:"|\')(.*?)(?:"|\')\s*\)'),
        re.compile(r'v-i18n="(.*?)"'),
        re.compile(r'"\{\{\{?\s*\'(.*?)\'\s*\|\s*i18n\}\}\}?"'),
        re.compile(r'{{_\s*"(.*?)"\s*}}'),
        re.compile(r'{{_\s*\'(.*?)\'\s*}}'),
    ]

    for directory, _, _ in os.walk(join(ROOT, 'js')):
        glob_patterns = (iglob(join(directory, g)) for g in globs)
        for filename in itertools.chain(*glob_patterns):
            print('Extracting messages from {0}'.format(green(filename)))
            content = codecs.open(filename, encoding='utf8').read()
            for regexp in regexps:
                for match in regexp.finditer(content):
                    key = match.group(1)
                    keys.append(key)
                    if key not in catalog:
                        catalog[key] = key

    with codecs.open(catalog_filename, 'w', encoding='utf8') as f:
        json.dump(catalog, f, sort_keys=True, indent=4, ensure_ascii=False,
                  encoding='utf8', separators=(',', ': '))

    for key, value in catalog.items():
        if key not in keys:
            not_found[key] = value

    with codecs.open(not_found_filename, 'w', encoding='utf8') as f:
        json.dump(not_found, f, sort_keys=True, indent=4, ensure_ascii=False,
                  encoding='utf8', separators=(',', ': '))


@task
def i18nc():
    '''Compile translations'''
    header('Compiling translations')
    lrun('python setup.py compile_catalog')


@task
def assets():
    '''Install and compile assets'''
    header('Building static assets')
    lrun('webpack -c --progress --config webpack.config.prod.js', pty=True)


@task(i18nc, assets)
def dist():
    '''Package for distribution'''
    header('Building a distribuable package')
    lrun('python setup.py bdist_wheel', pty=True)


@task
def watch():
    lrun('webpack -d -c --progress --watch', pty=True)
