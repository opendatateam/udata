# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from flask import current_app
from mongoengine.signals import post_save

from udata.search import adapter_catalog, reindex

log = logging.getLogger(__name__)


def reindex_model_on_save(sender, document, **kwargs):
    '''(Re)Index Mongo document on post_save'''
    if current_app.config.get('AUTO_INDEX'):
        reindex.delay(document)


class SearchAdapterMetaClass(type):
    '''Ensure any child class dispatch the signals'''
    def __new__(cls, name, bases, attrs):
        # Ensure any child class dispatch the signals
        adapter = super(SearchAdapterMetaClass, cls).__new__(cls, name, bases, attrs)
        # register the class in the catalog
        if adapter.model:
            adapter_catalog[adapter.model] = adapter
        # Automatically reindex objects on save
        post_save.connect(reindex_model_on_save, sender=adapter.model)
        return adapter


class ModelSearchAdapter(object):
    '''This class allow to describe and customize the search behavior for a given model'''
    model = None
    fields = None
    facets = None
    sorts = None
    filters = None
    mapping = None

    __metaclass__ = SearchAdapterMetaClass

    @classmethod
    def doc_type(cls):
        return cls.model.__name__

    @classmethod
    def serialize(cls, document):
        '''By default use the ``to_dict`` method and exclude ``_id``, ``_cls`` and ``owner`` fields'''
        return document.to_dict(exclude=('_id', '_cls', 'owner'))
