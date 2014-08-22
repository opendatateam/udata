# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from celery import Celery, Task

from udata.models import db

log = logging.getLogger(__name__)


class ContextTask(Task):
    abstract = True
    schedulable = None
    current_app = None

    def __call__(self, *args, **kwargs):
        with self.current_app.app_context():
            return super(ContextTask, self).__call__(*args, **kwargs)


celery = Celery(task_cls=ContextTask)


def job(name, **kwargs):
    '''A shortcut decorator for declaring jobs'''
    return celery.task(name=name, schedulable=True, **kwargs)


def schedulables():
    return [task for task in celery.tasks.values() if task.schedulable]


def init_app(app):
    celery.main = app.import_name

    default_name = app.config.get('MONGODB_SETTINGS', {}).get('DB', 'celery')
    app.config.setdefault('CELERY_MONGODB_SCHEDULER_DB', default_name)

    default_url = 'mongodb://{host}:{port}'.format(host=db.connection.host, port=db.connection.port)
    app.config.setdefault('CELERY_MONGODB_SCHEDULER_URL', default_url)

    celery.conf.update(app.config)

    ContextTask.current_app = app

    # Load core tasks
    import udata.core.metrics.tasks
    import udata.core.storages.tasks
    # import udata.core.search.tasks
    import udata.core.activity.tasks
    import udata.core.dataset.tasks
    import udata.core.reuse.tasks
    import udata.core.organization.tasks

    # Load plugins tasks
    for plugin in app.config['PLUGINS']:
        name = 'udata.ext.{0}.tasks'.format(plugin)
        try:
            __import__(name)
        except ImportError:
            pass
        except Exception as e:
            log.error('Error importing %s: %s', name, e)

    return celery
