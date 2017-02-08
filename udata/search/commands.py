# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from datetime import datetime

from flask_script import prompt_bool

from udata.commands import submanager
from udata.search import es, adapter_catalog

from elasticsearch.helpers import reindex as es_reindex

log = logging.getLogger(__name__)

m = submanager(
    'search',
    help='Search/Indexation related operations',
    description='Handle search and indexation related operations'
)

TIMESTAMP_FORMAT = '%Y-%m-%d-%H-%M'


def default_index_name():
    '''Build a time based index name'''
    return '-'.join([es.index_name, datetime.now().strftime(TIMESTAMP_FORMAT)])


def iter_adapters():
    '''Iter over adapter in predictable way'''
    adapters = adapter_catalog.values()
    return sorted(adapters, key=lambda a: a.model.__name__)


def index_model(index_name, adapter):
    ''' Indel all objects given a model'''
    model = adapter.model
    log.info('Indexing {0} objects'.format(model.__name__))
    qs = model.objects
    if hasattr(model.objects, 'visible'):
        qs = qs.visible()
    if adapter.exclude_fields:
        qs = qs.exclude(*adapter.exclude_fields)
    for obj in qs.timeout(False):
        if adapter.is_indexable(obj):
            try:
                adapter = adapter.from_model(obj)
                adapter.save(using=es.client, index=index_name)
            except:
                log.exception('Unable to index %s "%s"',
                              model.__name__, str(obj.id))


def set_alias(index_name, delete=True):
    '''
    Properly end an indexation by creating an alias.
    Previous alias is deleted if needed.
    '''
    log.info('Creating alias "{0}" on index "{1}"'.format(
        es.index_name, index_name))
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
    es.indices.refresh()


@m.option('-t', '--type', dest='doc_type', default=None,
          help='Only reindex a given type')
def reindex(doc_type=None):
    '''Reindex models'''
    doc_types_names = [m.__name__.lower() for m in adapter_catalog.keys()]
    if doc_type and not doc_type.lower() in doc_types_names:
        log.error('Unknown type %s', doc_type)

    index_name = default_index_name()
    log.info('Initiliazing index "{0}"'.format(index_name))
    es.initialize(index_name)
    for adapter in iter_adapters():
        if adapter.doc_type().lower() == doc_type.lower():
            index_model(index_name, adapter)
        else:
            log.info('Copying {0} objects to the new index'.format(
                     adapter.model.__name__))
            # Need upgrade to Elasticsearch-py 5.0.0
            # es.reindex({
            #     'source': {'index': es.index_name, 'type': adapter.doc_type()},
            #     'dest': {'index': index_name}
            # })
            # http://elasticsearch-py.readthedocs.io/en/master/api.html#elasticsearch.Elasticsearch.reindex
            # This method (introduced in Elasticsearch 2.3 but only in Elasticsearch-py 5.0.0)
            # triggers a server-side documents copy.
            # Instead we use this helper for meant for backward compatibility
            # but with poor performance as copy is client-side (scan+bulk)
            es_reindex(es.client, es.index_name, index_name, scan_kwargs={
                'doc_type': adapter.doc_type()
            })

    set_alias(index_name)


@m.option('-n', '--name', default=None, help='Optionnal index name')
@m.option('-d', '--delete', default=False, action='store_true',
          help='Delete previously aliased indices')
@m.option('-f', '--force', default=False, action='store_true',
          help='Do not prompt on deletion')
def init(name=None, delete=False, force=False):
    '''Initialize or rebuild the search index'''
    index_name = name or default_index_name()
    log.info('Initiliazing index "{0}"'.format(index_name))
    if es.indices.exists(index_name):
        if force or prompt_bool(('Index {0} will be deleted, are you sure ?'
                                 .format(index_name))):
            es.indices.delete(index_name)
        else:
            exit(-1)

    es.initialize(index_name)

    for adapter in iter_adapters():
        index_model(index_name, adapter)
    set_alias(index_name, delete=delete)
