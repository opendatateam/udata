import json
import logging
from collections import Counter
from urllib.parse import urlparse

import click
import redis
from flask import current_app

from udata.commands import cli, exit_with_error
from udata.tasks import celery, router

log = logging.getLogger(__name__)


@cli.group("worker")
def grp():
    """Worker related operations"""
    pass


@grp.command()
def start():
    """Start a worker"""
    worker = celery.Worker()
    worker.start()
    return worker.exitcode


def status_print_task(count, biggest_task_name, munin=False):
    if munin:
        # Munin expect all values, including zeros
        print("%s.value %s" % (format_field_for_munin(count[0]), count[1]))
    elif count[1] > 0:
        # We only display tasks with items in queue for readability
        print("* %s : %s" % (count[0].ljust(biggest_task_name), count[1]))


def status_print_config(queue):
    if not queue:
        exit_with_error("--munin-config called without a --queue parameter")
    tasks = [n for n, q in get_tasks().items() if q == queue]
    print("graph_title Waiting tasks for queue %s" % queue)
    print("graph_vlabel Nb of tasks")
    print("graph_category celery")
    for task in tasks:
        print("%s.label %s" % (format_field_for_munin(task), short_name(task)))


def status_print_queue(queue, munin=False):
    r = get_redis_connection()
    if not munin:
        print("-" * 40)
    queue_length = r.llen(queue)
    if not munin:
        print('Queue "%s": %s task(s)' % (queue, queue_length))
    counter = Counter({n: 0 for n, q in get_tasks().items() if q == queue})
    biggest_task_name = 0
    for task in r.lrange(queue, 0, -1):
        task = json.loads(task)
        task_name = task["headers"]["task"]
        if len(task_name) > biggest_task_name:
            biggest_task_name = len(task_name)
        counter[task_name] += 1
    for count in counter.most_common():
        status_print_task(count, biggest_task_name, munin=munin)


def format_field_for_munin(field):
    return field.replace(".", "__").replace("-", "_")


def get_queues(queue):
    queues = [q.name for q in current_app.config["CELERY_TASK_QUEUES"]]
    if queue:
        queues = [q for q in queues if q == queue]
    if not len(queues):
        exit_with_error("Error: no queue found")
    return queues


def get_redis_connection():
    parsed_url = urlparse(current_app.config["CELERY_BROKER_URL"])
    db = parsed_url.path[1:] if parsed_url.path else 0
    return redis.StrictRedis(host=parsed_url.hostname, port=parsed_url.port, db=db)


def get_task_queue(name, cls):
    return (router(name, [], {}, None, task=cls) or {}).get("queue", "default")


def short_name(name):
    if "." not in name:
        return name
    return name.rsplit(".", 1)[1]


def get_tasks():
    """Get a list of known tasks with their routing queue"""
    return {
        name: get_task_queue(name, cls)
        for name, cls in celery.tasks.items()
        # Exclude celery internal tasks
        if not name.startswith("celery.")
        # Exclude udata test tasks
        and not name.startswith("test-")
    }


@grp.command()
def tasks():
    """Display registered tasks with their queue"""
    tasks = get_tasks()
    longest = max(tasks.keys(), key=len)
    size = len(longest)
    for name, queue in sorted(tasks.items()):
        print("* {0}: {1}".format(name.ljust(size), queue))


@grp.command()
@click.option("-q", "--queue", help="Queue to be analyzed", default=None)
@click.option("-m", "--munin", is_flag=True, help="Output in a munin plugin compatible format")
@click.option(
    "-c", "--munin-config", is_flag=True, help="Output in a munin plugin config compatible format"
)
def status(queue, munin, munin_config):
    """List queued tasks aggregated by name"""
    if munin_config:
        return status_print_config(queue)
    queues = get_queues(queue)
    for queue in queues:
        status_print_queue(queue, munin=munin)
    if not munin:
        print("-" * 40)
