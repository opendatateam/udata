# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import pytest

from udata.tasks import celery, task, job
from udata.utils import unique_string


TASKS = [
    ({}, 'default', None),
    ({'queue': 'low'}, 'low', 'low.{name}'),
    ({'queue': 'low', 'routing_key': 'key'}, 'low', 'key'),
    ({'routing_key': 'key'}, None, 'key'),
    ({'route': 'low.topic'}, 'low', 'low.topic'),
    ({'route': 'low.topic', 'queue': 'q'}, 'low', 'low.topic'),
    ({'route': 'low.topic', 'routing_key': 'rk'}, 'low', 'low.topic'),
]

JOBS = [
    ({}, 'low', 'low.{name}'),
    ({'queue': 'high'}, 'high', 'high.{name}'),
    ({'queue': 'high', 'routing_key': 'key'}, 'high', 'key'),
    ({'routing_key': 'key'}, 'low', 'key'),
    ({'route': 'high.topic'}, 'high', 'high.topic'),
    ({'route': 'high.topic', 'queue': 'q'}, 'high', 'high.topic'),
    ({'route': 'high.topic', 'routing_key': 'rk'}, 'high', 'high.topic'),
]


def idify(params):
    '''Proper param display for easier debugging'''
    return [
        ', '.join('='.join(tup) for tup in row[0].items())
        or 'none'
        for row in params
    ]


def fake_task(*args, **kwargs):
    pass


@pytest.fixture
def route_to(app, mocker):

    def assertion(func, args, kwargs, queue, key=None):
        __tracebackhide__ = True

        decorator = func(*args, **kwargs) if args or kwargs else func
        router = celery.amqp.router

        # Celery instanciate only one task by name so we need unique names
        suffix = unique_string().replace('-', '_')
        fake_task.__name__ = b'task_{0}'.format(suffix)
        t = decorator(fake_task)

        options = t._get_exec_options()

        route = router.route(options, t.name, task_type=t)
        if queue:
            assert route['queue'].name == queue, 'queue mismatch'
        if key:
            key = key.format(name=t.name)
            assert route['routing_key'] == key, 'routing_key mismatch'
        return route

    return assertion


@pytest.mark.parametrize('kwargs,queue,key', TASKS, ids=idify(TASKS))
def test_tasks_routing(route_to, kwargs, queue, key):
    route_to(task, [], kwargs, queue, key)


@pytest.mark.parametrize('kwargs,queue,key', JOBS, ids=idify(JOBS))
def test_job_routing(route_to, kwargs, queue, key):
    route_to(job, [unique_string()], kwargs, queue, key)
