# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from urlparse import urlparse

from celery import Celery, Task
from celery.utils.log import get_task_logger
from celerybeatmongo.schedulers import MongoScheduler

from udata import entrypoints

log = logging.getLogger(__name__)


class ContextTask(Task):
    abstract = True
    schedulable = None
    current_app = None
    route = None
    default_queue = None
    default_routing_key = None

    def __call__(self, *args, **kwargs):
        with self.current_app.app_context():
            return super(ContextTask, self).__call__(*args, **kwargs)


class JobTask(ContextTask):
    abstract = True
    default_queue = 'low'

    @property
    def log(self):
        return get_task_logger(self.name)


class Scheduler(MongoScheduler):
    def apply_async(self, entry, **kwargs):
        '''A MongoScheduler storing the last task_id'''
        result = super(Scheduler, self).apply_async(entry, **kwargs)
        entry._task.last_run_id = result.id
        return result


celery = Celery(task_cls=ContextTask)


def router(name, args, kwargs, options, task=None, **kw):
    '''
    A celery router using the predeclared :class:`ContextTask`
    attributes (`router` or `default_queue` and/or `default routing_key`).
    '''
    # Fetch task by name if necessary
    task = task or celery.tasks.get(name)
    if not task:
        return
    # Single route param override everything
    if task.route:
        queue = task.route.split('.', 1)[0]
        return {'queue': queue, 'routing_key': task.route}
    # queue parameter, routing_key computed if not present
    if task.default_queue:
        key = task.default_routing_key
        key = key or '{0.default_queue}.{0.name}'.format(task)
        return {'queue': task.default_queue, 'routing_key': key}
    # only routing_key, queue should not be returned to fallback on default
    elif task.default_routing_key:
        return {'routing_key': task.default_routing_key}


def task(*args, **kwargs):
    for arg in 'queue', 'routing_key':
        if arg in kwargs:
            kwargs['default_{0}'.format(arg)] = kwargs.pop(arg)
    return celery.task(*args, **kwargs)


def job(name, **kwargs):
    '''A shortcut decorator for declaring jobs'''
    return task(name=name, schedulable=True, base=JobTask,
                bind=True, **kwargs)


def get_logger(name):
    logger = get_task_logger(name)
    return logger


def connect(signal, *args, **kwargs):
    def wrapper(func):
        t = task(func, *args, **kwargs)

        def call_task(item, **kwargs):
            t.delay(item, **kwargs)

        signal.connect(call_task, weak=False)
        return t
    return wrapper


@job('test-log')
def log_test(self):
    self.log.debug('This is a DEBUG message')
    self.log.info('This is an INFO message')
    self.log.warning('This is a WARNING message')
    self.log.error('This is a ERROR message')


@job('test-low-queue', queue='low')
@job('test-default-queue', queue='default')
@job('test-high-queue', queue='high')
def queue_test(self, raises=False):
    '''
    An empty task to test the queues.
    Set raise to True if you want a notification (ie. Sentry)
    '''
    self.log.info('Just a test task')
    if raises:
        raise Exception('Test task processing')


@job('test-error')
def error_test(self):
    self.log.info('There should be an error soon')
    raise Exception('There is an error')


def schedulables():
    return [task for task in celery.tasks.values() if task.schedulable]


def default_scheduler_config(url):
    parsed_url = urlparse(url)
    default_url = '{0}://{1}'.format(*parsed_url)
    return parsed_url.path[1:], default_url


def init_app(app):
    celery.main = app.import_name

    db, url = default_scheduler_config(app.config['MONGODB_HOST'])

    app.config.setdefault('CELERY_MONGODB_SCHEDULER_DB', db)
    app.config.setdefault('CELERY_MONGODB_SCHEDULER_URL', url)

    celery.conf.update(**dict(
        (k.replace('CELERY_', '').lower(), v)
        for k, v in app.config.items()
        if k.startswith('CELERY_')
    ))

    ContextTask.current_app = app

    # Load core tasks
    import udata.core.metrics.tasks  # noqa
    import udata.core.tags.tasks  # noqa
    import udata.core.activity.tasks  # noqa
    import udata.core.dataset.tasks  # noqa
    import udata.core.reuse.tasks  # noqa
    import udata.core.user.tasks  # noqa
    import udata.core.organization.tasks  # noqa
    import udata.core.followers.tasks  # noqa
    import udata.core.issues.tasks  # noqa
    import udata.core.discussions.tasks  # noqa
    import udata.core.badges.tasks  # noqa
    import udata.core.storages.tasks  # noqa
    import udata.harvest.tasks  # noqa

    entrypoints.get_enabled('udata.tasks', app)

    return celery
