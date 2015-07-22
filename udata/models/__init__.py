# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from collections import Iterable

from flask.ext.mongoengine import (
    MongoEngine, MongoEngineSessionInterface, Document, BaseQuerySet
)
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

    def __iter__(self):
        return iter(self.queryset.items)

    def __len__(self):
        return len(self.queryset.items)

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

    def bulk_list(self, ids):
        data = self.in_bulk(ids)
        return [data[id] for id in ids]

    def get_or_create(self, write_concern=None, auto_save=True,
                      *q_objs, **query):
        """Retrieve unique object or create, if it doesn't exist.

        Returns a tuple of ``(object, created)``, where ``object`` is
        the retrieved or created object and ``created`` is a boolean
        specifying whether a new object was created.

        Taken back from:

        https://github.com/MongoEngine/mongoengine/
        pull/1029/files#diff-05c70acbd0634d6d05e4a6e3a9b7d66b
        """
        defaults = query.pop('defaults', {})
        try:
            doc = self.get(*q_objs, **query)
            return doc, False
        except self._document.DoesNotExist:
            query.update(defaults)
            doc = self._document(**query)

            if auto_save:
                doc.save(write_concern=write_concern)
            return doc, True


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
from udata.core.badges.models import *
from udata.core.discussions.models import *
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

from udata.features.transfer.models import *


def init_app(app):
    if app.config['TESTING']:
        app.config['MONGODB_DB'] = '{MONGODB_DB}-test'.format(**app.config)
    db.init_app(app)
    for plugin in app.config['PLUGINS']:
        name = 'udata.ext.{0}.models'.format(plugin)
        try:
            __import__(name)
        except ImportError:
            pass
        except Exception as e:
            log.error('Error importing %s: %s', name, e)
