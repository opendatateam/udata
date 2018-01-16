# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from udata.commands import cli, success
from udata.app import cache

log = logging.getLogger(__name__)


@cli.group('cache')
def grp():
    '''
    Cache related operations.
    '''
    pass


@grp.command()
def flush():
    '''Flush the cache'''
    log.info('Flushing cache')
    cache.clear()
    success('Cache flushed')
