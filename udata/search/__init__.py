# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from os.path import join, dirname

from elasticsearch import Elasticsearch, JSONSerializer
from elasticsearch.helpers import scan
from flask import current_app, json
from speaklater import make_lazy_string

from udata.app import UDataJsonEncoder
from udata.tasks import celery

log = logging.getLogger(__name__)

adapter_catalog = {}

DEFAULT_PAGE_SIZE = 20

ANALYSIS_JSON = join(dirname(__file__), 'analysis.json')


class EsJSONSerializer(JSONSerializer):
    def default(self, data):
        return UDataJsonEncoder().default(data)


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
        mappings = [
            (adapter.doc_type(), adapter.mapping)
            for adapter in adapter_catalog.values()
            if adapter.mapping
        ]

        if es.indices.exists(self.index_name):
            for doc_type, mapping in mappings:
                if es.indices.exists_type(index=self.index_name,
                                          doc_type=doc_type):
                    es.indices.delete_mapping(index=self.index_name,
                                              doc_type=doc_type)
                es.indices.put_mapping(index=self.index_name,
                                       doc_type=doc_type, body=mapping)
        else:
            with open(ANALYSIS_JSON) as analysis:
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
    doctype = adapter.doc_type()
    if adapter.is_indexable(obj):
        log.info('Indexing %s (%s)', doctype, obj.id)
        es.index(index=es.index_name, doc_type=doctype,
                 id=obj.id, body=adapter.serialize(obj))
    elif es.exists(index=es.index_name, doc_type=doctype, id=obj.id):
        log.info('Unindexing %s (%s)', doctype, obj.id)
        es.delete(index=es.index_name, doc_type=doctype,
                  id=obj.id, refresh=True)
    else:
        log.info('Nothing to do for %s (%s)', doctype, obj.id)


from .adapter import ModelSearchAdapter, metrics_mapping  # noqa
from .query import SearchQuery  # noqa
from .result import SearchResult, SearchIterator  # noqa
from .fields import *  # noqa


def query(*adapters, **kwargs):
    return SearchQuery(*adapters, **kwargs).execute()


def iter(*adapters, **kwargs):
    return SearchQuery(*adapters, **kwargs).iter()


def multiquery(*queries):
    body = []
    for query in queries:
        body.append({'type': query.adapter.doc_type()})
        body.append(query.get_body())
    try:
        result = es.msearch(index=es.index_name, body=body)
    except:
        log.exception('Unable to perform multiquery')
        result = [{} for _ in range(len(queries))]

    return [
        SearchResult(query, response)
        for response, query in zip(result['responses'], queries)
    ]


def suggest(q, field, size=10):
    result = es.suggest(index=es.index_name, body={
        'suggestions': {
            'text': q,
            'completion': {
                'field': field,
                'size': size,
            }
        }
    })
    if 'suggestions' not in result:
        return []
    return result['suggestions'][0]['options']


def init_app(app):
    # Register core adapters
    import udata.core.user.search  # noqa
    import udata.core.dataset.search  # noqa
    import udata.core.reuse.search  # noqa
    import udata.core.organization.search  # noqa
    import udata.core.spatial.search  # noqa

    es.init_app(app)
