# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from os.path import join, dirname

from elasticsearch import Elasticsearch, JSONSerializer
from flask import current_app, json
from speaklater import make_lazy_string, is_lazy_string

from udata.tasks import celery

log = logging.getLogger(__name__)

adapter_catalog = {}

DEFAULT_PAGE_SIZE = 20


class EsJSONSerializer(JSONSerializer):
    def default(self, data):
        if is_lazy_string(data):
            return unicode(data)
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
        app.extensions['elasticsearch'] = Elasticsearch([app.config['ELASTICSEARCH_URL']], serializer=EsJSONSerializer())

    def __getattr__(self, item):
        if not 'elasticsearch' in current_app.extensions.keys():
            raise Exception('not initialised, did you forget to call init_app?')
        return getattr(current_app.extensions['elasticsearch'], item)


    @property
    def index_name(self):
        if current_app.config.get('TESTING'):
            return '{0}-test'.format(current_app.name)
        return current_app.name

    def initialize(self):
        '''Create or update indices and mappings'''
        mappings = [
            (adapter.doc_type(), adapter.mapping)
            for adapter in adapter_catalog.values()
            if adapter.mapping
        ]
        if es.indices.exists(self.index_name):
            for doc_type, mapping in mappings:
                es.indices.put_mapping(index=self.index_name, doc_type=doc_type, body=mapping)
        else:
            filename = join(dirname(__file__), 'analysis.json')
            with open(filename) as analysis:
                es.indices.create(self.index_name, {
                    'mappings': dict(mappings),
                    'settings': {'analysis': json.load(analysis)},
                })


es = ElasticSearch()


def get_i18n_analyzer():
    return '{0}_analyzer'.format(current_app.config['DEFAULT_LANGUAGE'])

i18n_analyzer = make_lazy_string(get_i18n_analyzer)


@celery.task
def reindex(obj):
    adapter = adapter_catalog.get(obj.__class__)
    log.info('Indexing %s (%s)', adapter.doc_type(), obj.id)

    es.index(index=es.index_name, doc_type=adapter.doc_type(), id=obj.id, body=adapter.serialize(obj))


# from . import fields
from .adapter import ModelSearchAdapter
from .query import SearchQuery
from .result import SearchResult
from .fields import *

# Import core adapters
from udata.core.user.search import UserSearch
from udata.core.dataset.search import DatasetSearch
from udata.core.reuse.search import ReuseSearch
from udata.core.organization.search import OrganizationSearch


def query(*adapters, **kwargs):
    return SearchQuery(*adapters, **kwargs).execute()


def multiquery(*queries):
    body = []
    for query in queries:
        body.append({'type': query.adapter.doc_type()})
        body.append(query.get_body())
    try:
        result = es.msearch(index=es.index_name, body=body)
    except:
        result = [{} for _ in range(len(queries))]
    return [
        SearchResult(query, response)
        for response, query in zip(result['responses'], queries)
    ]


def init_app(app):
    es.init_app(app)
