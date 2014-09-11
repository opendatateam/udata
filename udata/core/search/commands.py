# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from udata.commands import manager
from udata.search import es, adapter_catalog

log = logging.getLogger(__name__)


@manager.option('-t', '--type', dest='doc_type', default=None, help='Only reindex a given type')
def reindex(doc_type=None):
    '''Reindex models'''
    for model, adapter in adapter_catalog.items():
        if not doc_type or doc_type == adapter.doc_type():
            print 'Reindexing {0} objects'.format(model.__name__)
            if es.indices.exists_type(index=es.index_name, doc_type=adapter.doc_type()):
                es.indices.delete_mapping(index=es.index_name, doc_type=adapter.doc_type())
            es.indices.put_mapping(index=es.index_name, doc_type=adapter.doc_type(), body=adapter.mapping)
            qs = model.objects.visible() if hasattr(model.objects, 'visible') else model.objects
            for obj in qs.timeout(False):
                es.index(index=es.index_name, doc_type=adapter.doc_type(), id=obj.id, body=adapter.serialize(obj))
    es.indices.refresh(index=es.index_name)
