# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from collections import Iterable

from flask.ext.mongoengine import MongoEngine, MongoEngineSessionInterface, Document, BaseQuerySet
from mongoengine.base import TopLevelDocumentMetaclass
from mongoengine.signals import pre_save, post_save

from flask.ext.fs.mongo import FileField, ImageField

from udata.utils import Paginable

from .badges_field import BadgesField
from .datetime_fields import DateField, DateRange, Datetimed
from .extras_fields import ExtrasField, Extra
from .slug_fields import SlugField
from .uuid_fields import AutoUUIDField

log = logging.getLogger(__name__)


class UDataMongoEngine(MongoEngine):
    '''Customized mongoengine with extra fields types and helpers'''
    def __init__(self, app=None):
        super(UDataMongoEngine, self).__init__(app)
        self.BadgesField = BadgesField
        self.DateField = DateField
        self.Datetimed = Datetimed
        self.Extra = Extra
        self.ExtrasField = ExtrasField
        self.SlugField = SlugField
        self.AutoUUIDField = AutoUUIDField
        self.Document = UDataDocument
        self.DomainModel = DomainModel
        self.DateRange = DateRange
        self.BaseQuerySet = UDataQuerySet
        self.BaseDocumentMetaclass = TopLevelDocumentMetaclass
        self.FileField = FileField
        self.ImageField = ImageField
        self.post_save = post_save
        self.pre_save = pre_save


def serialize(value):
    if hasattr(value, 'to_dict'):
        return value.to_dict()
    elif isinstance(value, Iterable) and not isinstance(value, basestring):
        return [serialize(val) for val in value]
    else:
        return value


class DBPaginator(Paginable):
    '''A simple paginable implementation'''
    def __init__(self, queryset):
        self.queryset = queryset

    @property
    def page(self):
        return self.queryset.page

    @property
    def page_size(self):
        return self.queryset.per_page

    @property
    def total(self):
        return self.queryset.total

    @property
    def objects(self):
        return self.queryset.items


class UDataQuerySet(BaseQuerySet):
    def paginate(self, page, per_page, error_out=True):
        result = super(UDataQuerySet, self).paginate(page, per_page, error_out)
        return DBPaginator(result)


class UDataDocument(Document):
    meta = {
        'abstract': True,
        'queryset_class': UDataQuerySet,
    }

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
from udata.core.spatial.models import *
from udata.core.metrics.models import *
from udata.core.issues.models import *
from udata.core.followers.models import *
from udata.core.user.models import *
from udata.core.organization.models import *
from udata.core.site.models import *
from udata.core.dataset.models import *
from udata.core.reuse.models import *
from udata.core.activity.models import *
from udata.core.topic.models import *
from udata.core.post.models import *
from udata.core.jobs.models import *


def init_app(app):
    db.init_app(app)
    for plugin in app.config['PLUGINS']:
        name = 'udata.ext.{0}.models'.format(plugin)
        try:
            __import__(name)
        except ImportError:
            pass
        except Exception as e:
            log.error('Error importing %s: %s', name, e)
