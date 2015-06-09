# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import json
import random

import requests
from celery.utils.log import get_task_logger
from flask import current_app
from udata.tasks import job
from udata.models import Activity, Metrics

from .models import Dataset, DatasetIssue, DatasetDiscussion, FollowDataset

log = get_task_logger(__name__)


@job('purge-datasets')
def purge_datasets(self):
    for dataset in Dataset.objects(deleted__ne=None):
        log.info('Purging dataset "{0}"'.format(dataset))
        # Remove followers
        FollowDataset.objects(following=dataset).delete()
        # Remove issues
        DatasetIssue.objects(subject=dataset).delete()
        # Remove discussions
        DatasetDiscussion.objects(subject=dataset).delete()
        # Remove activity
        Activity.objects(related_to=dataset).delete()
        # Remove metrics
        Metrics.objects(object_id=dataset.id).delete()
        # Remove
        dataset.delete()


@job('crawl-resources')
def crawl_resources(self):
    """Ask croquemort to crawl 500 random URLs from datasets."""
    urls = [r.url
            for d in Dataset.objects.only('resources.url')
            for r in d.resources]
    random.shuffle(urls)
    checked_urls = urls[:500]
    CROQUEMORT_URL = current_app.config.get('CROQUEMORT_URL')
    if CROQUEMORT_URL is None:
        return
    check_many_url = '{CROQUEMORT_URL}/check/many'.format(
        CROQUEMORT_URL=CROQUEMORT_URL)
    group_name = 'datagouvfr'
    log.info('Checking URLs under group {name}'.format(name=group_name))
    response = requests.post(check_many_url, data=json.dumps({
        'urls': checked_urls,
        'group': group_name,
    }))
    log.info('URLs checked with group hash {hash}'.format(
        hash=response.json()['group-hash']))
