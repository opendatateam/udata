# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

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
        'build', 'dist', 'cover', 'docs/_build',
        '**/*.pyc', '*.egg-info', '.tox'
    ]
    if bower:
        patterns.append('udata/static/bower')
    if node:
        patterns.append('node_modules')
    for pattern in patterns:
        print('Removing {0}'.format(pattern))
        run('cd {0} && rm -rf {1}'.format(ROOT, pattern))


@task
def test():
    '''Run tests suite'''
    run('cd {0} && nosetests --rednose --force-color udata'.format(ROOT), pty=True)


@task
def cover():
    '''Run tests suite with coverage'''
    run('cd {0} && nosetests --rednose --force-color \
        --with-coverage --cover-html --cover-package=udata'.format(ROOT), pty=True)


@task
def doc():
    '''Build the documentation'''
    run('cd {0}/doc && make html'.format(ROOT), pty=True)


@task
def qa():
    '''Run a quality report'''
    run('flake8 {0}/udata'.format(ROOT))


@task
def serve():
    '''Run a development server'''
    run('cd {0} && python manage.py serve -d -r'.format(ROOT), pty=True)


@task
def work(loglevel='info'):
    '''Run a development worker'''
    run('celery -A udata.worker worker --purge --autoreload -l %s' % loglevel)


@task
def beat(loglevel='info'):
    '''Run celery beat process'''
    run('celery -A udata.worker beat -l %s' % loglevel)


@task
def i18n():
    '''Extract translatable strings'''
    run('python setup.py extract_messages')
    run('python setup.py update_catalog')
    run('udata i18njs -d udata udata/static')


@task
def i18nc():
    '''Compile translations'''
    print(cyan('Compiling translations'))
    run('cd {0} && python setup.py compile_catalog'.format(ROOT))


@task
def assets():
    '''Install and compile assets'''
    print(cyan('Building static assets'))
    lrun('cd {0} && webpack -c --progress --config webpack.config.prod.js'.format(ROOT), pty=True)


@task(i18nc, assets)
def dist():
    '''Package for distribution'''
    print(cyan('Building a distribuable package'))
    lrun('python setup.py bdist_wheel', pty=True)


@task
def watch():
    lrun('webpack -d -c --progress --watch', pty=True)
