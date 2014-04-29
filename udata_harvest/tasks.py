# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.tasks import celery


from .models import Harvester


@celery.task
def harvest(harvester_id):
    harvester = Harvester.objects.get(harvester_id)

