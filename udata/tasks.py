# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from celery import Celery
from celery.schedules import crontab

from udata.core import MODULES

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

    # Load all core tasks
    for module in MODULES:
        try:
            __import__('udata.core.{0}.tasks'.format(module))
        except ImportError:
            pass
        except Exception as e:
            log.error('Unable to import %s: %s', module, e)

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
