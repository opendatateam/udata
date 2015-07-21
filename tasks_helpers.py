# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

from os.path import join, abspath, dirname

from invoke import run

#: Project absolute root path
ROOT = abspath(join(dirname(__file__)))


def color(code):
    '''A simple ANSI color wrapper factory'''
    return lambda t: '\033[{0}{1}\033[0;m'.format(code, t)


green = color('1;32m')
red = color('1;31m')
cyan = color('1;36m')
purple = color('1;35m')


def header(text):
    '''Display an header'''
    print(green('>> {0}'.format(text)))


def info(text):
    '''Display informations'''
    print(cyan('>>> {0}'.format(text)))


def subinfo(text):
    print(purple('>>>> {0}'.format(text)))


def lrun(command, *args, **kwargs):
    '''Run a local command from project root'''
    return run('cd {0} && {1}'.format(ROOT, command), *args, **kwargs)


def nrun(command, *args, **kwargs):
    '''Run node.js command from project root'''
    return lrun('cd {0} && node_modules/.bin/{1}'.format(ROOT, command), *args, **kwargs)
