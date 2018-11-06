import logging

from click import echo

from flask import current_app

from udata import entrypoints
from udata.commands import cli, white, OK, KO, green, red

from udata.features.identicon.backends import get_config as avatar_config


log = logging.getLogger(__name__)


@cli.group('info')
def grp():
    '''Display some details about the local environment'''
    pass


def by_name(e):
    return e.name


def is_active(ep, actives):
    return green(OK) if ep.name in actives else red(KO)


@grp.command()
def config():
    '''Display some details about the local configuration'''
    if hasattr(current_app, 'settings_file'):
        log.info('Loaded configuration from %s', current_app.settings_file)

    log.info(white('Current configuration'))
    for key in sorted(current_app.config):
        if key.startswith('__') or not key.isupper():
            continue
        echo('{0}: {1}'.format(white(key), current_app.config[key]))


@grp.command()
def plugins():
    '''Display some details about the local plugins'''
    plugins = current_app.config['PLUGINS']
    for name, description in entrypoints.ENTRYPOINTS.items():
        echo('{0} ({1})'.format(white(description), name))
        if name == 'udata.themes':
            actives = [current_app.config['THEME']]
        elif name == 'udata.avatars':
            actives = [avatar_config('provider')]
        else:
            actives = plugins
        for ep in sorted(entrypoints.iter_all(name), key=by_name):
            echo('> {0}: {1}'.format(ep.name, is_active(ep, actives)))
