# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import bson
import datetime
import logging

from elasticsearch import Elasticsearch
from elasticsearch.helpers import scan
from elasticsearch_dsl import FacetedSearch
from elasticsearch_dsl import MultiSearch, Search, Index as ESIndex
from elasticsearch_dsl.serializer import AttrJSONSerializer
from flask import current_app
from mongoengine.signals import post_save, post_delete
from speaklater import is_lazy_string
from werkzeug.local import LocalProxy

from udata.tasks import task


from . import analysis

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
        # using the app factory pattern _app_ctx_stack.top is None so what
        # do we register on? app.extensions looks a little hackish (I don't
        # know flask well enough to be sure), but that's how it's done in
        # flask-pymongo so let's use it for now.
        if app.config['TESTING'] and 'ELASTICSEARCH_URL_TEST' in app.config:
                app.config['ELASTICSEARCH_URL'] = app.config['ELASTICSEARCH_URL_TEST']
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
        basename = current_app.config['ELASTICSEARCH_INDEX_BASENAME']
        if current_app.config.get('TESTING'):
            return '{0}-test'.format(basename)
        return basename

    def scan(self, body, **kwargs):
        return scan(self.client, query=body, **kwargs)

    def initialize(self, index_name=None):
        '''Create or update indices and mappings'''
        index_name = index_name or self.index_name
        index = Index(index_name, using=es.client)
        for adapter_class in adapter_catalog.values():
            index.doc_type(adapter_class)
        index.create()


es = ElasticSearch()


class Index(ESIndex):
    '''
    An Elasticsearch DSL index handling filters and analyzers registeration.
    See: https://github.com/elastic/elasticsearch-dsl-py/issues/410
    '''
    def _get_mappings(self):
        mappings, _ = super(Index, self)._get_mappings()
        return mappings, {
            'analyzer': {
                a._name: a.get_definition() for a in analysis.analyzers
            },
            'filter': {f._name: f.get_definition() for f in analysis.filters},
        }


def get_i18n_analyzer():
    # Get a specific i18n analyser or fallback to the standard if it doesn't exist
    language = current_app.config['DEFAULT_LANGUAGE']
    try:
        return getattr(analysis, '{0}_analyzer'.format(language))
    except AttributeError:
        return getattr(analysis, 'standard')

i18n_analyzer = LocalProxy(lambda: get_i18n_analyzer())


@task(route='high.search')
def reindex(obj):
    model = obj.__class__
    adapter_class = adapter_catalog.get(model)
    if adapter_class.is_indexable(obj):
        log.info('Indexing %s (%s)', model.__name__, obj.id)
        try:
            adapter = adapter_class.from_model(obj)
            adapter.save(using=es.client, index=es.index_name)
        except Exception:
            log.exception('Unable to index %s "%s"', model.__name__, str(obj.id))
    elif adapter_class.exists(obj.id, using=es.client, index=es.index_name):
        log.info('Unindexing %s (%s)', model.__name__, obj.id)
        try:
            adapter = adapter_class.from_model(obj)
            adapter.delete(using=es.client, index=es.index_name)
        except Exception:
            log.exception('Unable to index %s "%s"', model.__name__, str(obj.id))
    else:
        log.info('Nothing to do for %s (%s)', model.__name__, obj.id)


@task(route='high.search')
def unindex(obj):
    model = obj.__class__
    adapter_class = adapter_catalog.get(model)
    if adapter_class.exists(obj.id, using=es.client, index=es.index_name):
        log.info('Unindexing %s (%s)', model.__name__, obj.id)
        try:
            adapter = adapter_class.from_model(obj)
            adapter.delete(using=es.client, index=es.index_name)
        except Exception:
            log.exception('Unable to unindex %s "%s"', model.__name__, str(obj.id))
    else:
        log.info('Nothing to do for %s (%s)', model.__name__, obj.id)


def reindex_model_on_save(sender, document, **kwargs):
    '''(Re/Un)Index Mongo document on post_save'''
    if current_app.config.get('AUTO_INDEX'):
        reindex.delay(document)


def unindex_model_on_delete(sender, document, **kwargs):
    '''Unindex Mongo document on post_delete'''
    if current_app.config.get('AUTO_INDEX'):
        unindex.delay(document)


def register(adapter):
    '''Register a search adapter'''
    # register the class in the catalog
    if adapter.model and adapter.model not in adapter_catalog:
        adapter_catalog[adapter.model] = adapter
        # Automatically (re|un)index objects on save/delete
        post_save.connect(reindex_model_on_save, sender=adapter.model)
        post_delete.connect(unindex_model_on_delete, sender=adapter.model)
    return adapter


from .adapter import ModelSearchAdapter, metrics_mapping_for  # noqa
from .query import SearchQuery  # noqa
from .result import SearchResult  # noqa
from .fields import *  # noqa


def facets_for(adapter, params):
    facets = params.pop('facets', [])
    if not adapter.facets:
        return []
    if isinstance(facets, basestring):
        facets = [facets]
    if facets is True or 'all' in facets:
        return adapter.facets.keys()
    else:
        # Return all requested facets
        # r facets required for value filtering
        return [
            f for f in adapter.facets.keys()
            if f in facets or f in params
        ]


def adapter_for(model_or_adapter):
    if issubclass(model_or_adapter, ModelSearchAdapter):
        return model_or_adapter
    else:
        return adapter_catalog[model_or_adapter]


def search_for(model_or_adapter, **params):
    if isinstance(model_or_adapter, FacetedSearch):
        return model_or_adapter
    adapter = adapter_for(model_or_adapter)
    facets = facets_for(adapter, params)
    facet_search = adapter.facet_search(*facets)
    return facet_search(params)


def query(model, **params):
    search = search_for(model, **params)
    return search.execute()


def iter(model, **params):
    params['facets'] = True
    search = search_for(model, **params)
    search._s.aggs._params = {}  # Remove aggregations.
    for result in search._s.scan():
        yield result.model.objects.get(id=result.meta['id'])


def multisearch(*models, **params):
    ms = MultiSearch(using=es.client, index=es.index_name)
    queries = []
    for model in models:
        s = search_for(model, **params)
        ms = ms.add(s._s)
        queries.append(s)
    responses = ms.execute()
    return [
        # _d_ is the only way to access the raw data
        # allowing to rewrap response in a FacetedSearch
        # because default multisearch loose facets
        SearchResult(query, response._d_)
        for query, response in zip(queries, responses)
    ]


def suggest(q, field, size=10):
    s = Search(using=es.client, index=es.index_name)
    s = s.suggest('suggestions', q, completion={
        'field': field,
        'size': size,
    })
    result = s.execute_suggest().to_dict()
    try:
        suggestions = result.get('suggestions', [])[0]['options']
        return suggestions
    except (IndexError, AttributeError):
        return []


def init_app(app):
    # Register core adapters
    import udata.core.user.search  # noqa
    import udata.core.dataset.search  # noqa
    import udata.core.reuse.search  # noqa
    import udata.core.organization.search  # noqa
    import udata.core.spatial.search  # noqa

    es.init_app(app)
