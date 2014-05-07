# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from collections import Iterable
from importlib import import_module

from flask.ext.mongoengine import MongoEngine, MongoEngineSessionInterface, Document, BaseQuerySet
from mongoengine.base import TopLevelDocumentMetaclass
from mongoengine.signals import pre_save, post_save

from udata.core import MODULES

from .datetime_fields import DateField, DateRange, Datetimed
from .slug_fields import SlugField
from .uuid_fields import AutoUUIDField

log = logging.getLogger(__name__)


class UDataMongoEngine(MongoEngine):
    '''Customized mongoengine with extra fields types and helpers'''
    def __init__(self, app=None):
        super(UDataMongoEngine, self).__init__(app)
        self.DateField = DateField
        self.Datetimed = Datetimed
        self.SlugField = SlugField
        self.AutoUUIDField = AutoUUIDField
        self.Document = UDataDocument
        self.DateRange = DateRange
        self.BaseQuerySet = BaseQuerySet
        self.BaseDocumentMetaclass = TopLevelDocumentMetaclass
        self.post_save = post_save
        self.pre_save = pre_save


def serialize(value):
    if hasattr(value, 'to_dict'):
        return value.to_dict()
    elif isinstance(value, Iterable) and not isinstance(value, basestring):
        return [serialize(val) for val in value]
    else:
        return value


class UDataDocument(Document):
    meta = {'abstract': True}

    def to_dict(self, exclude=None):
        excluded_keys = set(exclude or [])
        excluded_keys.add('_cls')
        return dict((
            (key, serialize(value))
            for key, value in self.to_mongo().items()
            if key not in excluded_keys
        ))


db = UDataMongoEngine()
session_interface = MongoEngineSessionInterface(db)


# Load all models mixins
# Load all core models
loc = locals()
for module in MODULES:
    try:
        models = import_module('udata.core.{0}.models'.format(module))
        for model in models.__all__:
            loc[model] = getattr(models, model)
    except ImportError as e:
        pass
    except Exception as e:
        log.error('Unable to import %s: %s', module, e)
del loc


def init_app(app):
    db.init_app(app)
    for plugin in app.config['PLUGINS']:
        try:
            __import__('udata.ext.{0}.models'.format(plugin))
        except:
            pass
