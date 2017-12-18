# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from urlparse import urlparse

from celery import Celery, Task
from celery.utils.log import get_task_logger
from celerybeatmongo.schedulers import MongoScheduler

log = logging.getLogger(__name__)


class ContextTask(Task):
    abstract = True
    schedulable = None
    current_app = None

    def __call__(self, *args, **kwargs):
        with self.current_app.app_context():
            return super(ContextTask, self).__call__(*args, **kwargs)


class JobTask(ContextTask):
    abstract = True

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


def task(*args, **kwargs):
    return celery.task(*args, **kwargs)


def job(name, **kwargs):
    '''A shortcut decorator for declaring jobs'''
    return celery.task(name=name, schedulable=True, base=JobTask,
                       bind=True, **kwargs)


def get_logger(name):
    logger = get_task_logger(name)
    return logger


def connect(signal):
    def wrapper(func):
        t = task(func)

        def call_task(item, **kwargs):
            t.delay(item, **kwargs)

        signal.connect(call_task, weak=False)
        return t
    return wrapper


@job('log-test')
def helloworld(self):
    self.log.debug('This is a DEBUG message')
    self.log.info('This is an INFO message')
    self.log.warning('This is a WARNING message')
    self.log.error('This is a ERROR message')


@job('error-test')
def error_test_task(self):
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
    import udata.harvest.tasks  # noqa

    # Load plugins tasks
    for plugin in app.config['PLUGINS']:
        name = 'udata_{0}.tasks'.format(plugin)
        try:
            __import__(name)
        except ImportError:
            pass
        except Exception as e:
            log.error('Error importing %s: %s', name, e)

    return celery
