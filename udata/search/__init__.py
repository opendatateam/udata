# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from importlib import import_module
from os.path import join, dirname

from elasticsearch import Elasticsearch, JSONSerializer
from flask import current_app, json
from speaklater import make_lazy_string, is_lazy_string

from udata.core import MODULES


log = logging.getLogger(__name__)

adapter_catalog = {}


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

    def contribute(self):
        # from . import fields
        from . import fields
        for name in fields.__all__:
            setattr(self, name, getattr(fields, name))
        from . import adapter
        for name in adapter.__all__:
            setattr(self, name, getattr(adapter, name))

        # Load all core search adapters
        for module in MODULES:
            try:
                module = import_module('udata.core.{0}.search'.format(module))
                for name in module.__all__:
                    setattr(self, name, getattr(module, name))
            except ImportError as e:
                pass
            except Exception as e:
                log.error('Unable to import %s: %s', module, e)



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


# from . import fields
from .fields import *
from .adapter import *


def init_app(app):
    es.init_app(app)

# Load all core search adapters
loc = locals()
for module in MODULES:
    try:
        module = import_module('udata.core.{0}.search'.format(module))
        for cls in module.__all__:
            loc[cls] = getattr(module, cls)
    except ImportError as e:
        pass
    except Exception as e:
        log.error('Unable to import %s: %s', module, e)
del loc
