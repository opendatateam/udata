# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from udata.commands import submanager
from udata.app import cache

log = logging.getLogger(__name__)


m = submanager(
    'cache',
    help='Cache related operations',
    description='Handle all cache related operations and maintenance'
)


@m.command
def flush():
    '''Flush the cache'''
    print('Flusing cache')
    cache.clear()
    print('Cache flushed')
