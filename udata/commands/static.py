# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import os
import shutil

import click

from glob import iglob
from os import makedirs
from os.path import exists, join, isdir

from flask import current_app

from udata.commands import cli

log = logging.getLogger(__name__)


@cli.command()
@click.argument('path', default='public')
@click.option('-ni', '--no-input', is_flag=True, help="Disable input prompts")
def collect(path, no_input):
    '''Collect static files'''
    if exists(path):
        msg = '"%s" directory already exists and will be erased'
        log.warning(msg, path)
        if not no_input:
            click.confirm('Are you sure?', abort=True)

        log.info('Deleting static directory "%s"', path)
        shutil.rmtree(path)

    prefix = current_app.static_url_path or current_app.static_folder
    if prefix.startswith('/'):
        prefix = prefix[1:]
    destination = join(path, prefix)
    log.info('Copying application assets into "%s"', destination)
    shutil.copytree(current_app.static_folder, destination)

    for blueprint in current_app.blueprints.values():
        if blueprint.has_static_folder:
            prefix = current_app.static_prefixes.get(blueprint.name)
            prefix = prefix or blueprint.url_prefix or ''
            prefix += blueprint.static_url_path or ''
            if prefix.startswith('/'):
                prefix = prefix[1:]

            log.info('Copying %s assets to %s', blueprint.name, prefix)
            destination = join(path, prefix)
            copy_recursive(blueprint.static_folder, destination)

    for prefix, source in current_app.config['STATIC_DIRS']:
        log.info('Copying %s to %s', source, prefix)
        destination = join(path, prefix)
        copy_recursive(source, destination)

    log.info('Done')


def copy_recursive(source, destination):
    if not exists(destination):
        makedirs(destination)
    for filename in iglob(join(source, '*')):
        if isdir(filename):
            suffix = filename.replace(source, '')
            if suffix.startswith(os.sep):
                suffix = suffix[1:]
            copy_recursive(filename, join(destination, suffix))
        else:
            shutil.copy(filename, destination)
