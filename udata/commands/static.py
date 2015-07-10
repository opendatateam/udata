# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import os
import shutil

from glob import iglob
from os import makedirs
from os.path import exists, join, isdir
from sys import exit

from flask import current_app
from flask.ext.script import prompt_bool

from udata import theme
from udata.commands import manager

log = logging.getLogger(__name__)


@manager.option('path', nargs='?', default='static', help='target path')
@manager.option('-ni', '--no-input', dest="input",
    action='store_false', help="Disable input prompts")
def collect(path, input):
    '''Collect static files'''
    if exists(path):
        print('"{0}" directory already exists and will be erased'.format(path))
        if input and not prompt_bool('Are you sure'):
            exit(-1)

        print('Deleting static directory {0}'.format(path))
        shutil.rmtree(path)

    # print('Copying assets into "{0}"'.format(path))
    # shutil.copytree(theme.assets.directory, path)

    for prefix, source in manager.app.config['STATIC_DIRS']:
        print('Copying %s to %s' % (source, prefix))
        destination = join(path, prefix)
        copy_recursive(source, destination)

    print('Done')


def copy_recursive(source, destination):
    if not exists(destination):
        makedirs(destination)
    for filename in iglob(join(source, '*')):
        print(filename)
        if isdir(filename):
            suffix = filename.replace(source, '')
            if suffix.startswith(os.sep):
                suffix = suffix[1:]
            copy_recursive(filename, join(destination, suffix))
        else:
            shutil.copy(filename, destination)
