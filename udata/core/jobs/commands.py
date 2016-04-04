# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import logging

from udata.commands import submanager
from udata.tasks import schedulables, celery

log = logging.getLogger(__name__)


m = submanager(
    'job',
    help='Jobs related operations',
    description='Handle all jobs related operations and maintenance'
)


@m.option('name', help='The job name')
@m.option('-d', '--delay', action='store_true', default=False,
          help='Run the job asynchronously on a worker')
@m.option('-a', '--args', nargs='*', help='job arguments')
@m.option('-k', '--kwargs', nargs='*', help='job keyword arguments')
def run(name, delay, args, kwargs):
    args = args or []
    kwargs = dict(k.split() for k in kwargs) if kwargs else {}
    if name not in celery.tasks:
        log.error('Job %s not found', name)
    job = celery.tasks[name]
    if delay:
        log.info('Sending job %s', name)
        job.delay(*args, **kwargs)
        log.info('Job sended to workers')
    else:
        log.info('Running job %s', name)
        job.run(*args, **kwargs)
        log.info('Job %s done', name)


@m.command
def list():
    '''List all availables jobs'''
    for job in schedulables():
        log.info(job.name)
