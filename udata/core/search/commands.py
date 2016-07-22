# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from datetime import date

from flask_script import prompt_bool

from udata.commands import submanager
from udata.search import es, adapter_catalog, Index

log = logging.getLogger(__name__)

m = submanager(
    'search',
    help='Search/Indexation related operations',
    description='Handle search and indexation related operations'
)


@m.option('-t', '--type', dest='doc_type', default=None,
          help='Only reindex a given type')
def reindex(doc_type=None):
    '''Reindex models'''
    name = es.index_name
    adapters = adapter_catalog.items()
    # Ensure that adapters are indexed in the same order.
    adapters.sort()
    for model, adapter_class in adapters:
        doctype = adapter_class.doc_type
        if not doc_type or doc_type.lower() == doctype.lower():
            log.info('Reindexing {0} objects'.format(model.__name__))
            if es.indices.exists_type(index=name, doc_type=doctype):
                log.warn(("The index {name} already exists and his mapping "
                          "will not be updated with that command, you need "
                          "to use the ` search init` command if you want to "
                          "update the mapping.").format(name=name))
            else:
                es.indices.put_mapping(index=name,
                                       doc_type=doctype,
                                       body=adapter_class.mapping)
            qs = model.objects
            if hasattr(model.objects, 'visible'):
                qs = qs.visible()
            for obj in qs.timeout(False):
                adapter = adapter_class.from_model(obj)
                if adapter_class.is_indexable(obj):
                    try:
                        adapter.save(using=es.client, index=es.index_name)
                    except:
                        log.exception(
                            'Unable to index %s "%s"',
                            model.__name__, str(obj.id))
                elif es.exists(index=name, doc_type=doctype, id=obj.id):
                    log.info('Unindexing %s (%s)', doctype, obj.id)
                    adapter.delete(using=es.client, index=es.index_name)
                else:
                    log.info('Nothing to do for %s (%s)', doctype, obj.id)
    es.indices.refresh(index=name)


@m.option('-n', '--name', default=None, help='Optionnal index name')
@m.option('-d', '--delete', default=False, action='store_true',
          help='Delete previously aliased indices')
@m.option('-f', '--force', default=False, action='store_true',
          help='Do not prompt on deletion')
def init(name=None, delete=False, force=False):
    '''Initialize or rebuild the search index'''
    index_name = name or '-'.join([es.index_name, date.today().isoformat()])
    log.info('Initiliazing index "{0}"'.format(index_name))
    if es.indices.exists(index_name):
        if force or prompt_bool(('Index {0} will be deleted, are you sure ?'
                                 .format(index_name))):
            es.indices.delete(index_name)
        else:
            exit(-1)

    index = Index(index_name, using=es.client)
    for adapter_class in adapter_catalog.values():
        index.doc_type(adapter_class)
    index.create()

    adapters = adapter_catalog.items()
    # Ensure that adapters are indexed in the same order.
    adapters.sort()
    for model, adapter_class in reversed(adapters):
        log.info('Indexing {0} objects'.format(model.__name__))
        qs = model.objects
        if hasattr(model.objects, 'visible'):
            qs = qs.visible()
        for obj in qs.timeout(False):
            if adapter_class.is_indexable(obj):
                try:
                    adapter = adapter_class.from_model(obj)
                    adapter.save(using=es.client, index=index_name)
                except:
                    log.exception('Unable to index %s "%s"',
                                  model.__name__, str(obj.id))

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
