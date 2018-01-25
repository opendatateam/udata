# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

import logging

from . import cli, success, error, header

logger = logging.getLogger(__name__)


@cli.group('test')
def test():
    '''Some commands for testing purpose'''


@test.command()
def log():
    '''Test logging'''
    header('header')
    success('success')
    error('error')
    logger.debug('debug')
    logger.info('info')
    logger.info('success')
    logger.info('info\nmulti\nlines')
    logger.warning('warning')
    logger.error('error')
    logger.critical('critical')
    try:
        raise Exception('An exception')
    except Exception:
        logger.exception('exception')
