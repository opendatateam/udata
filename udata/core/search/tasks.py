# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from celery.utils.log import get_task_logger

from udata.tasks import celery
from udata.search import es, adapter_catalog


log = get_task_logger(__name__)


@celery.task
def reindex(obj):
    adapter = adapter_catalog.get(obj.__class__)
    log.info('Indexing %s (%s)', adapter.doc_type(), obj.id)

    es.index(index=es.index_name, doc_type=adapter.doc_type(), id=obj.id, body=adapter.serialize(obj))
