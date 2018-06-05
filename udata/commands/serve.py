# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import os

import click

from flask import current_app
from flask.cli import pass_script_info, DispatchingApp

from werkzeug.serving import run_simple

from udata.commands import cli


log = logging.getLogger(__name__)


@cli.command(short_help='Runs a development server.')
@click.option('--host', '-h', default='127.0.0.1',
              help='The interface to bind to.')
@click.option('--port', '-p', default=7000,
              help='The port to bind to.')
@click.option('-r/-nr', '--reload/--no-reload', default=None,
              help='Enable or disable the reloader.  By default the reloader '
              'is active if debug is enabled.')
@click.option('-d/-nd', '--debugger/--no-debugger', default=None,
              help='Enable or disable the debugger.  By default the debugger '
              'is active if debug is enabled.')
@click.option('--eager-loading/--lazy-loader', default=None,
              help='Enable or disable eager loading.  By default eager '
              'loading is enabled if the reloader is disabled.')
@click.option('--with-threads/--without-threads', default=True,
              help='Enable or disable multithreading.')
@pass_script_info
def serve(info, host, port, reload, debugger, eager_loading, with_threads):
    '''
    Runs a local udata development server.

    This local server is recommended for development purposes only but it
    can also be used for simple intranet deployments.

    By default it will not support any sort of concurrency at all
    to simplify debugging.
    This can be changed with the --with-threads option which will enable basic
    multithreading.

    The reloader and debugger are by default enabled if the debug flag of
    Flask is enabled and disabled otherwise.
    '''
    # Werkzeug logger is special and is required
    # with this configuration for development server
    logger = logging.getLogger('werkzeug')
    logger.setLevel(logging.INFO)
    logger.handlers = []

    debug = current_app.config['DEBUG']
    if reload is None:
        reload = bool(debug)
    if debugger is None:
        debugger = bool(debug)
    if eager_loading is None:
        eager_loading = not reload

    app = DispatchingApp(info.load_app, use_eager_loading=eager_loading)

    settings = os.environ.get('UDATA_SETTINGS',
                              os.path.join(os.getcwd(), 'udata.cfg'))
    run_simple(host, port, app, use_reloader=reload,
               use_debugger=debugger, threaded=with_threads,
               extra_files=[settings])
