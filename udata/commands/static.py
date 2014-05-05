# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import shutil

from glob import iglob
from os import makedirs
from os.path import exists, join, isdir
from sys import exit

from flask.ext.script import prompt_bool
from webassets.script import CommandLineEnvironment

from udata.commands import manager
from udata.frontend import assets

log = logging.getLogger(__name__)


@manager.option('path', nargs='?', default='static', help='target path')
@manager.option('-ni', '--no-input', dest="input",
    action='store_false', help="Disable input prompts")
def static(path, input):
    '''Compile and collect static files'''
    log = logging.getLogger('webassets')
    log.addHandler(logging.StreamHandler())
    log.setLevel(logging.DEBUG)

    if exists(path):
        print('"{0}" directory already exists and will be erased'.format(path))
        if input and not prompt_bool('Are you sure'):
            exit(-1)

    cmdenv = CommandLineEnvironment(assets, log)
    # cmdenv.clean()
    cmdenv.build(production=True)

    print('Deleting static directory {0}'.format(path))
    shutil.rmtree(path)

    print('Copying assets into "{0}"'.format(path))
    shutil.copytree(assets.directory, path)

    for prefix, source in manager.app.config['STATIC_DIRS']:
        print('Copying %s to %s', source, prefix)
        destination_path = join(path, prefix)
        if not exists(destination_path):
            makedirs(destination_path)
        for filename in iglob(join(source, '*')):
            print(filename)
            if isdir(filename):
                continue
            shutil.copy(filename, destination_path)
        # shutil.copy(static_dir, path)

    print('Done')
