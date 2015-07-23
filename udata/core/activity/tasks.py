# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# from celery.utils.log import get_task_logger
from udata.tasks import celery


@celery.task
def write_activity(cls, actor, related_to, organization=None, **kwargs):
    cls.objects.create(actor=actor, related_to=related_to,
                       organization=organization, kwargs=kwargs)
