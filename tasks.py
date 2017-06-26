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

from tasks_helpers import ROOT, info, header, lrun, green

I18N_DOMAIN = 'udata'


@task
def clean(ctx, node=False, translations=False, all=False):
    '''Cleanup all build artifacts'''
    header('Clean all build artifacts')
    patterns = [
        'build', 'dist', 'cover', 'docs/_build',
        '**/*.pyc', '*.egg-info', '.tox', 'udata/static/*'
    ]
    if node or all:
        patterns.append('node_modules')
    if translations or all:
        patterns.append('udata/translations/*/LC_MESSAGES/udata.mo')
    for pattern in patterns:
        info(pattern)
    lrun('rm -rf {0}'.format(' '.join(patterns)))


@task
def update(ctx, migrate=False):
    '''Perform a development update'''
    msg = 'Update all dependencies'
    if migrate:
        msg += ' and migrate data'
    header(msg)
    info('Updating Python dependencies')
    lrun('pip install -r requirements/develop.pip')
    lrun('pip install -e .')
    info('Updating JavaScript dependencies')
    lrun('npm install')
    if migrate:
        info('Migrating database')
        lrun('udata db migrate')


@task
def test(ctx, fast=False):
    '''Run tests suite'''
    header('Run tests suite')
    cmd = 'nosetests --rednose --force-color udata'
    if fast:
        cmd = ' '.join([cmd, '--stop'])
    lrun(cmd)


@task
def cover(ctx):
    '''Run tests suite with coverage'''
    header('Run tests suite with coverage')
    lrun('nosetests --rednose --force-color \
        --with-coverage --cover-html --cover-package=udata')


@task
def jstest(ctx, watch=False):
    '''Run Karma tests suite'''
    header('Run Karma/Mocha test suite')
    cmd = 'npm run -s test:{0}'.format('watch' if watch else 'unit')
    lrun(cmd)


@task
def doc(ctx):
    '''Build the documentation'''
    header('Building documentation')
    lrun('mkdocs serve', pty=True)


@task
def qa(ctx):
    '''Run a quality report'''
    header('Performing static analysis')
    info('Python static analysis')
    flake8_results = lrun('flake8 udata --jobs 1', pty=True, warn=True)
    info('JavaScript static analysis')
    eslint_results = lrun('npm -s run lint', pty=True, warn=True)
    if flake8_results.failed or eslint_results.failed:
        exit(flake8_results.return_code or eslint_results.return_code)
    print(green('OK'))


@task
def serve(ctx, host='localhost'):
    '''Run a development server'''
    lrun('python manage.py serve -d -r -h %s' % host)


@task
def work(ctx, loglevel='info'):
    '''Run a development worker'''
    run('celery -A udata.worker worker --purge --autoreload -l %s' % loglevel,
        pty=True)


@task
def beat(ctx, loglevel='info'):
    '''Run celery beat process'''
    run('celery -A udata.worker beat -l %s' % loglevel)


@task
def i18n(ctx):
    '''Extract translatable strings'''
    header('Extract translatable strings')

    info('Extract Python strings')
    lrun('python setup.py extract_messages')
    lrun('python setup.py update_catalog')

    info('Extract JavaScript strings')
    keys = set()
    catalog = {}
    catalog_filename = join(ROOT, 'js', 'locales',
                            '{}.en.json'.format(I18N_DOMAIN))
    if exists(catalog_filename):
        with codecs.open(catalog_filename, encoding='utf8') as f:
            catalog = json.load(f)

    globs = '*.js', '*.vue', '*.hbs'
    regexps = [
        re.compile(r'(?:|\.|\s|\{)_\(\s*(?:"|\')(.*?)(?:"|\')\s*(?:\)|,)'),  # JS _('trad')
        re.compile(r'v-i18n="(.*?)"'),  # Vue.js directive v-i18n="trad"
        re.compile(r'"\{\{\{?\s*\'(.*?)\'\s*\|\s*i18n\}\}\}?"'),  # Vue.js filter {{ 'trad'|i18n }}
        re.compile(r'{{_\s*"(.*?)"\s*}}'),  # Handlebars {{_ "trad" }}
        re.compile(r'{{_\s*\'(.*?)\'\s*}}'),  # Handlebars {{_ 'trad' }}
        re.compile(r'\:[a-z0-9_\-]+="\s*_\(\'(.*?)\'\)\s*"'),  # Vue.js binding :prop="_('trad')"
    ]

    for directory, _, _ in os.walk(join(ROOT, 'js')):
        glob_patterns = (iglob(join(directory, g)) for g in globs)
        for filename in itertools.chain(*glob_patterns):
            print('Extracting messages from {0}'.format(green(filename)))
            content = codecs.open(filename, encoding='utf8').read()
            for regexp in regexps:
                for match in regexp.finditer(content):
                    key = match.group(1)
                    key = key.replace('\\n', '\n')
                    keys.add(key)
                    if key not in catalog:
                        catalog[key] = key

    # Remove old/not found translations
    for key in catalog.keys():
        if key not in keys:
            del catalog[key]

    with codecs.open(catalog_filename, 'w', encoding='utf8') as f:
        json.dump(catalog, f, sort_keys=True, indent=4, ensure_ascii=False,
                  encoding='utf8', separators=(',', ': '))


@task
def i18nc(ctx):
    '''Compile translations'''
    header('Compiling translations')
    lrun('python setup.py compile_catalog')


@task
def assets_build(ctx):
    '''Install and compile assets'''
    header('Building static assets')
    lrun('npm run assets:build', pty=True)


@task
def widgets_build(ctx):
    '''Compile and minify widgets'''
    header('Building widgets')
    lrun('npm run widgets:build', pty=True)


@task
def assets_watch(ctx):
    '''Build assets on change'''
    lrun('npm run assets:watch', pty=True)


@task
def widgets_watch(ctx):
    '''Build widgets on changes'''
    lrun('npm run widgets:watch', pty=True)


@task(clean, i18nc, assets_build, widgets_build)
def dist(ctx, buildno=None):
    '''Package for distribution'''
    header('Building a distribuable package')
    cmd = ['python setup.py']
    if buildno:
        cmd.append('egg_info -b {0}'.format(buildno))
    cmd.append('bdist_wheel')
    lrun(' '.join(cmd), pty=True)
