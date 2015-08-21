# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

from os.path import join, abspath, dirname, exists

from invoke import run, task

ROOT = abspath(join(dirname(__file__)))
I18N_DOMAIN = 'udata-harvest'


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
        'build', 'dist', 'cover', 'docs/_build', 'udata_harvest/static',
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


@task
def cover():
    '''Run tests suite with coverage'''
    lrun('nosetests --rednose --force-color \
        --with-coverage --cover-html --cover-package=udata_me', pty=True)


@task
def qa():
    '''Run a quality report'''
    print(cyan('Running Flake8 report'))
    run('flake8 {0}/udata_harvest'.format(ROOT))
    print(green('OK'))


@task
def i18n():
    '''
    Extract translatables strings
    '''
    print(cyan('Extracting Python strings'))
    lrun('python setup.py extract_messages')
    lrun('python setup.py update_catalog')


@task
def build():
    # print(cyan('Compiling translations'))
    # lrun('python setup.py compile_catalog')
    pass


@task(build)
def dist():
    '''Package for distribution'''
    print(cyan('Building a distribuable package'))
    lrun('python setup.py bdist_wheel', pty=True)


@task(test, qa, dist, default=True)
def all():
    pass
