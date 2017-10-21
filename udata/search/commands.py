# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import sys
import signal

from contextlib import contextmanager
from datetime import datetime

from flask_script import prompt_bool
from flask_script.commands import InvalidCommand

from udata.commands import submanager
from udata.search import es, adapter_catalog


from elasticsearch.helpers import reindex as es_reindex, streaming_bulk

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


def iter_qs(qs, adapter):
    '''Safely iterate over a DB QuerySet yielding ES documents'''
    for obj in qs.no_dereference().timeout(False):
        if adapter.is_indexable(obj):
            doc = adapter.from_model(obj).to_dict(include_meta=True)
            yield doc


def iter_for_index(docs, index_name):
    '''Iter over ES documents ensuring a given index'''
    for doc in docs:
        doc['_index'] = index_name
        yield doc


def index_model(index_name, adapter):
    ''' Indel all objects given a model'''
    model = adapter.model
    log.info('Indexing {0} objects'.format(model.__name__))
    qs = model.objects
    if hasattr(model.objects, 'visible'):
        qs = qs.visible()
    if adapter.exclude_fields:
        qs = qs.exclude(*adapter.exclude_fields)

    docs = iter_qs(qs, adapter)
    docs = iter_for_index(docs, index_name)

    for ok, info in streaming_bulk(es.client, docs, raise_on_error=False):
        if not ok:
            log.error('Unable to index %s "%s": %s', model.__name__,
                      info['index']['_id'], info['index']['error'])


def disable_refresh(index_name):
    '''
    Disable refresh to optimize indexing

    See: https://www.elastic.co/guide/en/elasticsearch/reference/master/indices-update-settings.html#bulk
    '''  # noqa
    es.indices.put_settings(index=index_name, body={
        'index': {
            'refresh_interval': '-1'
        }
    })


def enable_refresh(index_name):
    '''
    Enable refresh after indexing and force merge

    See: https://www.elastic.co/guide/en/elasticsearch/reference/master/indices-update-settings.html#bulk
    '''  # noqa
    es.indices.put_settings(index=index_name, body={
        'index': {
            'refresh_interval': '1s'
        }
    })
    es.indices.forcemerge(index=index_name)


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


@contextmanager
def handle_error(index_name, keep=False):
    '''
    Handle errors while indexing.
    In case of error, properly log it, remove the index and exit.
    If `keep` is `True`, index is not deleted.
    '''
    # Handle keyboard interrupt
    signal.signal(signal.SIGINT, signal.default_int_handler)
    signal.signal(signal.SIGTERM, signal.default_int_handler)
    try:
        yield
    except KeyboardInterrupt:
        log.warning('Interrupted by signal')
    except Exception as e:
        log.error(e)
    if not keep:
        log.info('Removing index %s', index_name)
        es.indices.delete(index=index_name)
    sys.exit(-1)


@m.option(dest='models', nargs='+', metavar='model',
          help='Model to reindex')
@m.option('-k', '--keep', default=False, action='store_true',
          help='Keep index in case of error')
def reindex(models, keep=False):
    '''Reindex models'''
    doc_types_names = [m.__name__.lower() for m in adapter_catalog.keys()]
    models = [model.lower().rstrip('s') for model in models]
    for model in models:
        if model not in doc_types_names:
            log.error('Unknown model %s', model)
            sys.exit(-1)

    index_name = default_index_name()
    log.info('Initiliazing index "{0}"'.format(index_name))
    es.initialize(index_name)
    disable_refresh(index_name)
    with handle_error(index_name, keep):
        for adapter in iter_adapters():
            if adapter.doc_type().lower() in models:
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

    enable_refresh(index_name)
    set_alias(index_name)


@m.option('-n', '--name', default=None, help='Optionnal index name')
@m.option('-d', '--delete', default=False, action='store_true',
          help='Delete previously aliased indices')
@m.option('-f', '--force', default=False, action='store_true',
          help='Do not prompt on deletion')
@m.option('-k', '--keep', default=False, action='store_true',
          help='Keep index in case of error')
def init(name=None, delete=False, force=False, keep=False):
    '''Initialize or rebuild the search index'''
    index_name = name or default_index_name()
    log.info('Initiliazing index "{0}"'.format(index_name))
    if es.indices.exists(index_name):
        if force or prompt_bool(('Index {0} will be deleted, are you sure ?'
                                 .format(index_name))):
            es.indices.delete(index_name)
        else:
            sys.exit(-1)

    es.initialize(index_name)
    disable_refresh(index_name)

    with handle_error(index_name, keep):
        for adapter in iter_adapters():
            index_model(index_name, adapter)

    enable_refresh(index_name)
    set_alias(index_name, delete=delete)
