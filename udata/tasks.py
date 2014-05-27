# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from celery import Celery
from celery.schedules import crontab

log = logging.getLogger(__name__)


celery = Celery()


def init_app(app):
    celery.main = app.import_name
    celery.conf.update(app.config)

    celery.conf['CELERYBEAT_SCHEDULE'] = {
        'bump-metrics-every-nights': {
            'task': 'bump-metrics',
            'schedule': crontab(hour=0, minute=0),
        },
    }

    TaskBase = celery.Task

    class ContextTask(TaskBase):
        abstract = True

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)
    celery.Task = ContextTask

    # Load core tasks
    import udata.core.metrics.tasks
    import udata.core.storages.tasks
    # import udata.core.search.tasks
    import udata.core.activity.tasks

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
