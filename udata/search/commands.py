# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import sys
import signal

import click

from contextlib import contextmanager
from datetime import datetime

from flask import current_app

from udata.commands import cli, IS_TTY
from udata.search import es, adapter_catalog


from elasticsearch.helpers import reindex as es_reindex, streaming_bulk

log = logging.getLogger(__name__)


@cli.group('search')
def grp():
    '''Search/Indexation related operations'''
    pass


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
            try:
                doc = adapter.from_model(obj).to_dict(include_meta=True)
                yield doc
            except Exception as e:
                model = adapter.model.__name__
                log.error('Unable to index %s "%s": %s', model, str(obj.id),
                          str(e), exc_info=True)


def iter_for_index(docs, index_name):
    '''Iterate over ES documents ensuring a given index'''
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
    Enable refresh and force merge. To be used after indexing.

    See: https://www.elastic.co/guide/en/elasticsearch/reference/master/indices-update-settings.html#bulk
    '''  # noqa
    refresh_interval = current_app.config['ELASTICSEARCH_REFRESH_INTERVAL']
    es.indices.put_settings(index=index_name, body={
        'index': {'refresh_interval': refresh_interval}
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
    has_error = False
    try:
        yield
    except KeyboardInterrupt:
        print('')  # Proper warning message under the "^C" display
        log.warning('Interrupted by signal')
        has_error = True
    except Exception as e:
        log.error(e)
        has_error = True
    if has_error:
        if not keep:
            log.info('Removing index %s', index_name)
            es.indices.delete(index=index_name)
        sys.exit(-1)


@grp.command()
@click.argument('models', nargs=-1, metavar='[<model> ...]')
@click.option('-n', '--name', default=None, help='Optionnal index name')
@click.option('-f', '--force', is_flag=True, help='Do not prompt on deletion')
@click.option('-k', '--keep', is_flag=True, help='Do not delete indexes')
def index(models=None, name=None, force=False, keep=False):
    '''
    Initialize or rebuild the search index

    Models to reindex can optionnaly be specified as arguments.
    If not, all models are reindexed.
    '''
    index_name = name or default_index_name()

    doc_types_names = [m.__name__.lower() for m in adapter_catalog.keys()]
    models = [model.lower().rstrip('s') for model in (models or [])]
    for model in models:
        if model not in doc_types_names:
            log.error('Unknown model %s', model)
            sys.exit(-1)

    log.info('Initiliazing index "{0}"'.format(index_name))
    if es.indices.exists(index_name):
        if IS_TTY and not force:
            msg = 'Index {0} will be deleted, are you sure?'
            click.confirm(msg.format(index_name), abort=True)
        es.indices.delete(index_name)

    es.initialize(index_name)

    with handle_error(index_name, keep):

        disable_refresh(index_name)
        for adapter in iter_adapters():
            if not models or adapter.doc_type().lower() in models:
                index_model(index_name, adapter)
            else:
                log.info('Copying {0} objects to the new index'.format(
                         adapter.model.__name__))
                # Need upgrade to Elasticsearch-py 5.0.0 to write:
                # es.reindex({
                #     'source': {'index': es.index_name, 'type': adapter.doc_type()},
                #     'dest': {'index': index_name}
                # })
                #
                # http://elasticsearch-py.readthedocs.io/en/master/api.html#elasticsearch.Elasticsearch.reindex
                # This method (introduced in Elasticsearch 2.3 but only in Elasticsearch-py 5.0.0)
                # triggers a server-side documents copy.
                # Instead we use this helper for meant for backward compatibility
                # but with poor performance as copy is client-side (scan+bulk)
                es_reindex(es.client, es.index_name, index_name, scan_kwargs={
                    'doc_type': adapter.doc_type()
                })

        enable_refresh(index_name)
    # At this step, we don't want error handler to delete the index
    # in case of error
    set_alias(index_name, delete=not keep)
