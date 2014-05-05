# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

# from flask.ext.script import Command, Option

from udata.commands import manager
from udata.search import es

log = logging.getLogger(__name__)


@manager.command
def init():
    '''Initialize or update data and indexes'''
    print 'Initialize or update ElasticSearch mappings'
    es.initialize()

    print 'TODO: Apply DB migrations if needed'
    print 'TODO: Feed initial data if needed'
    print 'TODO: create an user if needed'
