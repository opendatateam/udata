# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import bson
import datetime
import logging

from mongoengine.signals import post_save
from elasticsearch import Elasticsearch
from elasticsearch.helpers import scan
from elasticsearch_dsl import MultiSearch, Search, Index as ESIndex
from elasticsearch_dsl.serializer import AttrJSONSerializer
from flask import current_app
from werkzeug.local import LocalProxy
from speaklater import is_lazy_string

from udata.tasks import celery

from . import analyzers

log = logging.getLogger(__name__)

adapter_catalog = {}

DEFAULT_PAGE_SIZE = 20


class EsJSONSerializer(AttrJSONSerializer):
    # TODO: find a way to reuse UDataJsonEncoder?
    def default(self, data):
        if is_lazy_string(data):
            return unicode(data)
        elif isinstance(data, bson.objectid.ObjectId):
            return str(data)
        elif isinstance(data, datetime.datetime):
            return data.isoformat()
        elif hasattr(data, 'serialize'):
            return data.serialize()
        # Serialize Raw data for Document and EmbeddedDocument.
        elif hasattr(data, '_data'):
            return data._data
        else:
            return super(EsJSONSerializer, self).default(data)


class ElasticSearch(object):
    def __init__(self, app=None):
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        app.config.setdefault('ELASTICSEARCH_URL', 'localhost:9200')

        # using the app factory pattern _app_ctx_stack.top is None so what
        # do we register on? app.extensions looks a little hackish (I don't
        # know flask well enough to be sure), but that's how it's done in
        # flask-pymongo so let's use it for now.
        app.extensions['elasticsearch'] = Elasticsearch(
            [app.config['ELASTICSEARCH_URL']], serializer=EsJSONSerializer())

    def __getattr__(self, item):
        if 'elasticsearch' not in current_app.extensions.keys():
            raise Exception(
                'Not initialized, did you forget to call init_app?')
        return getattr(current_app.extensions['elasticsearch'], item)

    @property
    def client(self):
        if 'elasticsearch' not in current_app.extensions.keys():
            raise Exception(
                'Not initialized, did you forget to call init_app?')
        return current_app.extensions['elasticsearch']

    @property
    def index_name(self):
        if current_app.config.get('TESTING'):
            return '{0}-test'.format(current_app.name)
        return current_app.name

    def scan(self, body, **kwargs):
        return scan(self.client, query=body, **kwargs)

    def initialize(self):
        '''Create or update indices and mappings'''
        for adapter in adapter_catalog.values():
            adapter.init(using=self.client, index=self.index_name)


es = ElasticSearch()


class Index(ESIndex):
    '''
    An Elasticsearch DSL index handling filters and analyzers registeration.
    See: https://github.com/elastic/elasticsearch-dsl-py/issues/410
    '''
    def _get_mappings(self):
        mappings, _ = super(Index, self)._get_mappings()
        return mappings, analyzers.analysis_settings()


def get_i18n_analyzer():
    language = current_app.config['DEFAULT_LANGUAGE']
    return getattr(analyzers, '{0}_analyzer'.format(language))

i18n_analyzer = LocalProxy(lambda: get_i18n_analyzer())


@celery.task
def reindex(obj):
    adapter_class = adapter_catalog.get(obj.__class__)
    doctype = adapter_class.doc_type
    adapter = adapter_class(obj)
    if adapter.is_indexable(obj):
        log.info('Indexing %s (%s)', doctype, obj.id)
        adapter.save(using=es.client, index=es.index_name)
    elif es.exists(index=es.index_name, doc_type=doctype, id=obj.id):
        log.info('Unindexing %s (%s)', doctype, obj.id)
        adapter.delete(using=es.client, index=es.index_name)
    else:
        log.info('Nothing to do for %s (%s)', doctype, obj.id)


def reindex_model_on_save(sender, document, **kwargs):
    '''(Re/Un)Index Mongo document on post_save'''
    if current_app.config.get('AUTO_INDEX'):
        reindex.delay(document)


def register(adapter):
    '''Register a search adapter'''
    # register the class in the catalog
    if adapter.model and adapter.model not in adapter_catalog:
        adapter_catalog[adapter.model] = adapter
        # Automatically reindex objects on save
        post_save.connect(reindex_model_on_save, sender=adapter.model)
    return adapter


from .adapter import ModelSearchAdapter, metrics_mapping_for  # noqa
from .query import SearchQuery  # noqa
from .result import SearchResult, SearchIterator  # noqa
from .fields import *  # noqa


def query(*adapters, **kwargs):
    return SearchQuery(*adapters, **kwargs).execute()


def iter(*adapters, **kwargs):
    return SearchQuery(*adapters, **kwargs).iter()


def multisearch(*queries):
    ms = MultiSearch(using=es.client, index=es.index_name)
    for query in queries:
        qs = query.build_query()
        ms = ms.add(qs)
    responses = ms.execute()
    return responses


def suggest(q, field, size=10):
    s = Search(using=es.client, index=es.index_name)
    s = s.suggest('suggestions', q, completion={
        'field': field,
        'size': size,
    })
    result = s.execute_suggest()
    try:
        return result.suggestions[0]['options']
    except IndexError:
        return []


def init_app(app):
    # Register core adapters
    import udata.core.user.search  # noqa
    import udata.core.dataset.search  # noqa
    import udata.core.reuse.search  # noqa
    import udata.core.organization.search  # noqa
    import udata.core.spatial.search  # noqa

    es.init_app(app)
