# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# from celery.utils.log import get_task_logger
from udata.tasks import celery


@celery.task
def write_activity(cls, actor, as_organization=None, **kwargs):
    cls.objects.create(actor=actor, as_organization=as_organization, **kwargs)
