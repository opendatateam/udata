# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from datetime import date

from flask import json
from flask.ext.script import prompt_bool

from udata.commands import submanager
from udata.search import es, adapter_catalog, ANALYSIS_JSON

log = logging.getLogger(__name__)


m = submanager('search',
    help='Search/Indexation related operations',
    description='Handle search and indexation related operations'
)


@m.option('-t', '--type', dest='doc_type', default=None, help='Only reindex a given type')
@m.option('-n', '--name', default=None, help='Optionnal index name')
def reindex(name=None, doc_type=None):
    '''Reindex models'''
    for model, adapter in adapter_catalog.items():
        if not doc_type or doc_type.lower() == adapter.doc_type().lower():
            log.info('Reindexing {0} objects'.format(model.__name__))
            if es.indices.exists_type(index=es.index_name, doc_type=adapter.doc_type()):
                es.indices.delete_mapping(index=es.index_name, doc_type=adapter.doc_type())
            es.indices.put_mapping(index=es.index_name, doc_type=adapter.doc_type(), body=adapter.mapping)
            qs = model.objects.visible() if hasattr(model.objects, 'visible') else model.objects
            for obj in qs.timeout(False):
                try:
                    es.index(index=es.index_name, doc_type=adapter.doc_type(), id=obj.id, body=adapter.serialize(obj))
                except:
                    log.exception('Unable to index %s "%s"', model.__name__, str(obj.id))
    es.indices.refresh(index=es.index_name)


@m.option('-n', '--name', default=None, help='Optionnal index name')
@m.option('-d', '--delete', default=False, action='store_true', help='Delete previously aliased indices')
@m.option('-f', '--force', default=False, action='store_true', help='Do not prompt on deletion')
def init(name=None, delete=False, force=False):
    '''Initialize or rebuild the search index'''
    index_name = name or '-'.join([es.index_name, date.today().isoformat()])
    log.info('Initiliazing index "{0}"'.format(index_name))
    if es.indices.exists(index_name):
        if force or prompt_bool('Index {0} will be deleted, are you sure ?'.format(index_name)):
            es.indices.delete(index_name)
        else:
            exit(-1)
    mappings = [
        (adapter.doc_type(), adapter.mapping)
        for adapter in adapter_catalog.values()
        if adapter.mapping
    ]
    with open(ANALYSIS_JSON) as analysis:
        es.indices.create(index_name, {
            'mappings': dict(mappings),
            'settings': {'analysis': json.load(analysis)},
        })

    for model, adapter in adapter_catalog.items():
        log.info('Indexing {0} objects'.format(model.__name__))
        qs = model.objects.visible() if hasattr(model.objects, 'visible') else model.objects
        for obj in qs.timeout(False):
            try:
                es.index(index=index_name, doc_type=adapter.doc_type(), id=obj.id, body=adapter.serialize(obj))
            except:
                log.exception('Unable to index %s "%s"', model.__name__, str(obj.id))

    log.info('Creating alias "{0}" on index "{1}"'.format(es.index_name, index_name))
    if es.indices.exists_alias(name=es.index_name):
        alias = es.indices.get_alias(name=es.index_name)
        previous_indices = alias.keys()
        if index_name not in previous_indices:
            es.indices.put_alias(index=index_name, name=es.index_name)
        for index in previous_indices:
            if index != index_name:
                es.indices.delete_alias(index=index, name=es.index_name)
                if delete:
                    es.indices.delete(index=index)
    else:
        es.indices.put_alias(index=index_name, name=es.index_name)
