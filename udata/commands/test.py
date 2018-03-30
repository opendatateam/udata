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
    header('header é')
    success('success é')
    error('error é')
    error('error with string details é', 'ééé')
    error('error with object details é', Exception('ééé'))
    logger.debug('debug é')
    logger.info('info é')
    logger.info('info é with unicode interpolation %s', 'ééé')
    logger.info('info é with interpolations %s %d %f', 'ééé', 10, .1)
    logger.info('success é')
    logger.info('info\nmulti\nlines é')
    logger.warning('warning é')
    logger.error('error é')
    logger.critical('critical é')
    try:
        raise Exception('An exception é')
    except Exception:
        logger.exception('exception é')
