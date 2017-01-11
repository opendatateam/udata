# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from flask_script import Command

from udata.commands import manager
from udata.tasks import celery

log = logging.getLogger(__name__)


class Worker(Command):
    '''Run a celery worker'''
    def run(self, *args, **kwargs):
        celery.start()


manager.add_command('worker', Worker())
