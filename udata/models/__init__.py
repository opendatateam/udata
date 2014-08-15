# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from collections import Iterable

from flask.ext.mongoengine import MongoEngine, MongoEngineSessionInterface, Document, BaseQuerySet
from mongoengine.base import TopLevelDocumentMetaclass
from mongoengine.signals import pre_save, post_save

from .datetime_fields import DateField, DateRange, Datetimed
from .extras_fields import ExtrasField, Extra
from .slug_fields import SlugField
from .uuid_fields import AutoUUIDField

log = logging.getLogger(__name__)


class UDataMongoEngine(MongoEngine):
    '''Customized mongoengine with extra fields types and helpers'''
    def __init__(self, app=None):
        super(UDataMongoEngine, self).__init__(app)
        self.DateField = DateField
        self.Datetimed = Datetimed
        self.Extra = Extra
        self.ExtrasField = ExtrasField
        self.SlugField = SlugField
        self.AutoUUIDField = AutoUUIDField
        self.Document = UDataDocument
        self.DomainModel = DomainModel
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


class DomainModel(UDataDocument):
    '''Placeholder for inheritance'''
    pass


db = UDataMongoEngine()
session_interface = MongoEngineSessionInterface(db)


# Load all core models and mixins
from udata.core.metrics.models import *
from udata.core.issues.models import *
from udata.core.followers.models import *
from udata.core.user.models import *
from udata.core.dataset.models import *
from udata.core.reuse.models import *
from udata.core.organization.models import *
from udata.core.activity.models import *
from udata.core.topic.models import *
from udata.core.post.models import *


def init_app(app):
    db.init_app(app)
    for plugin in app.config['PLUGINS']:
        try:
            __import__('udata.ext.{0}.models'.format(plugin))
        except:
            pass
