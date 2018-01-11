# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

import logging

from . import cli

logger = logging.getLogger(__name__)


@cli.group()
def test():
    '''Some commands for testing purpose'''


@test.command()
def log():
    '''Test logging'''
    logger.debug('debug')
    logger.info('info')
    logger.info('info\nmulti\nlines')
    logger.warning('warning')
    logger.error('error')
    logger.critical('critical')
    try:
        raise Exception('An exception')
    except Exception:
        logger.exception('exception')
