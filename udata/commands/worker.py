# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
import logging
from collections import Counter
from urlparse import urlparse

import redis

from flask import current_app

from udata.commands import submanager
from udata.tasks import celery

log = logging.getLogger(__name__)

m = submanager(
    'worker',
    help='Worker related operations',
    description='Handle all worker related operations and maintenance'
)


@m.command
def start():
    """Start a worker"""
    celery.start()


@m.command
def status():
    """List queued tasks aggregated by name"""
    parsed_url = urlparse(current_app.config['CELERY_BROKER_URL'])
    db = parsed_url.path[1:] if parsed_url.path else 0
    r = redis.StrictRedis(host=parsed_url.hostname, port=parsed_url.port,
                          db=db)
    queues = [q.name for q in current_app.config['CELERY_TASK_QUEUES']]
    for queue in queues:
        print('-' * 40)
        queue_length = r.llen(queue)
        print('Queue "%s": %s task(s)' % (queue, queue_length))
        counter = Counter()
        biggest_task_name = 0
        for task in r.lrange(queue, 0, -1):
            task = json.loads(task)
            task_name = task['headers']['task']
            if len(task_name) > biggest_task_name:
                biggest_task_name = len(task_name)
            counter[task_name] += 1
        for count in counter.most_common():
            print('* %s : %s' % (count[0].ljust(biggest_task_name), count[1]))
    print('-' * 40)
