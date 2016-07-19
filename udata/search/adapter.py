# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import itertools
import logging

from flask import current_app
from mongoengine.signals import post_save
from elasticsearch_dsl import DocType, Integer, Float, Object

from udata.search import adapter_catalog, reindex
from udata.core.metrics import Metric
from udata.search import es

log = logging.getLogger(__name__)


def reindex_model_on_save(sender, document, **kwargs):
    '''(Re/Un)Index Mongo document on post_save'''
    if current_app.config.get('AUTO_INDEX'):
        reindex.delay(document)


class SearchAdapterMetaClass(type):
    '''Ensure any child class dispatch the signals'''
    def __new__(cls, name, bases, attrs):
        # Ensure any child class dispatch the signals
        adapter = super(SearchAdapterMetaClass, cls).__new__(
            cls, name, bases, attrs)
        # register the class in the catalog
        if adapter.model and adapter.model not in adapter_catalog:
            adapter_catalog[adapter.model] = adapter
            # Automatically reindex objects on save
            post_save.connect(reindex_model_on_save, sender=adapter.model)
        return adapter


class ModelSearchAdapter(DocType):
    """This class allow to describe and customize the search behavior."""
    model = None
    analyzer = None
    fields = None
    facets = None
    sorts = None
    filters = None
    mapping = None
    match_type = 'cross_fields'
    fuzzy = False

    @classmethod
    def doc_type(cls):
        return cls.model.__name__

    @classmethod
    def is_indexable(cls, document):
        return True

    @classmethod
    def serialize(cls, document):
        """By default use the ``to_dict`` method

        and exclude ``_id``, ``_cls`` and ``owner`` fields
        """
        return document.to_dict(exclude=('_id', '_cls', 'owner'))

    @classmethod
    def completer_tokenize(cls, value, min_length=3):
        '''Quick and dirty tokenizer for completion suggester'''
        tokens = list(itertools.chain(*[
            [m for m in n.split("'") if len(m) > min_length]
            for n in value.split(' ')
        ]))
        return list(set([value] + tokens + [' '.join(tokens)]))


metrics_mapping_types = {
    int: Integer,
    float: Float,
}

def metrics_mapping_for(cls):
    props = {}
    for name, metric in Metric.get_for(cls).items():
        props[metric.name] = metrics_types[metric.value_type]()
    return Object(properties=props)
