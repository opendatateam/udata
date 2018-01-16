# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
import logging
from collections import Counter
from urlparse import urlparse

import click
import redis

from celery.task.control import inspect
from flask import current_app

from udata.app import cache
from udata.commands import cli, exit_with_error
from udata.tasks import celery

log = logging.getLogger(__name__)


@cli.group('worker')
def grp():
    '''Worker related operations'''
    pass


TASKS_LIST_CACHE_KEY = 'worker-status-tasks'
# we're using an aggressive cache in order not to hit Celery every 5 min
TASKS_LIST_CACHE_DURATION = 60 * 60 * 24  # in seconds


@grp.command()
def start():
    '''Start a worker'''
    worker = celery.Worker()
    worker.start()
    return worker.exitcode


def status_print_task(count, biggest_task_name, munin=False):
    if not munin:
        print('* %s : %s' % (count[0].ljust(biggest_task_name), count[1]))
    else:
        print('%s.value %s' % (format_field_for_munin(count[0]), count[1]))


def status_print_config(queue):
    if not queue:
        exit_with_error('--munin-config called without a --queue parameter')
    tasks = cache.get(TASKS_LIST_CACHE_KEY) or []
    if not tasks:
        registered = inspect().registered_tasks()
        if registered:
            for w, tasks_list in registered.iteritems():
                tasks += [t for t in tasks_list if t not in tasks]
            cache.set(TASKS_LIST_CACHE_KEY, tasks,
                      timeout=TASKS_LIST_CACHE_DURATION)
    print('graph_title Waiting tasks for queue %s' % queue)
    print('graph_vlabel Nb of tasks')
    print('graph_category celery')
    for task in tasks:
        print('%s.label %s' % (format_field_for_munin(task), task))


def status_print_queue(queue, munin=False):
    r = get_redis_connection()
    if not munin:
        print('-' * 40)
    queue_length = r.llen(queue)
    if not munin:
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
        status_print_task(count, biggest_task_name, munin=munin)


def format_field_for_munin(field):
    return field.replace('.', '__').replace('-', '_')


def get_queues(queue):
    queues = [q.name for q in current_app.config['CELERY_TASK_QUEUES']]
    if queue:
        queues = [q for q in queues if q == queue]
    if not len(queues):
        exit_with_error('Error: no queue found')
    return queues


def get_redis_connection():
    parsed_url = urlparse(current_app.config['CELERY_BROKER_URL'])
    db = parsed_url.path[1:] if parsed_url.path else 0
    return redis.StrictRedis(host=parsed_url.hostname, port=parsed_url.port,
                             db=db)


@grp.command()
@click.option('-q', '--queue', help='Queue to be analyzed', default=None)
@click.option('-m', '--munin', is_flag=True,
              help='Output in a munin plugin compatible format')
@click.option('-c', '--munin-config', is_flag=True,
              help='Output in a munin plugin config compatible format')
def status(queue, munin, munin_config):
    """List queued tasks aggregated by name"""
    if munin_config:
        return status_print_config(queue)
    queues = get_queues(queue)
    for queue in queues:
        status_print_queue(queue, munin=munin)
    if not munin:
        print('-' * 40)
