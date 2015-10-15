# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

# from flask.ext.script import Command, Option

from udata.commands import manager, yellow
from udata.search import es

from .db import migrate

log = logging.getLogger(__name__)


@manager.command
def init():
    '''Initialize or update data and indexes'''
    log.info('Apply DB migrations if needed')
    migrate(record=True)

    log.info('Initialize or update ElasticSearch mappings')
    es.initialize()

    log.info('%s: Feed initial data if needed', yellow('TODO'))
    log.info('%s: Create an administrator', yellow('TODO'))
