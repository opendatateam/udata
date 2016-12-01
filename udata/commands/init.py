# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from udata.commands import manager, yellow
from udata.search import es

from .db import migrate
from .fixtures import generate_fixtures

log = logging.getLogger(__name__)


@manager.command
def init():
    '''Initialize or update data and indexes'''
    log.info('Initialize or update ElasticSearch mappings')
    es.initialize()

    log.info('Build sample fixture data')
    generate_fixtures()

    log.info('Apply DB migrations if needed')
    migrate(record=True)

    log.info('%s: Feed initial data if needed', yellow('TODO'))
