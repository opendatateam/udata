# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import importlib
import logging

from urlparse import urlparse

from bson import ObjectId, DBRef
from flask_mongoengine import MongoEngine, MongoEngineSessionInterface
from mongoengine.base import TopLevelDocumentMetaclass, get_document
from mongoengine.errors import ValidationError
from mongoengine.signals import pre_save, post_save

from flask_fs.mongo import FileField, ImageField

from .badges_field import BadgesField
from .taglist_field import TagListField
from .datetime_fields import DateField, DateRange, Datetimed
from .extras_fields import ExtrasField, Extra
from .slug_fields import SlugField
from .url_field import URLField
from .uuid_fields import AutoUUIDField
from .owned import Owned, OwnedQuerySet
from .queryset import UDataQuerySet
from .document import UDataDocument, DomainModel

log = logging.getLogger(__name__)


class UDataMongoEngine(MongoEngine):
    '''Customized mongoengine with extra fields types and helpers'''
    def __init__(self, app=None):
        super(UDataMongoEngine, self).__init__(app)
        self.BadgesField = BadgesField
        self.TagListField = TagListField
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
        self.URLField = URLField
        self.ValidationError = ValidationError
        self.ObjectId = ObjectId
        self.DBRef = DBRef
        self.Owned = Owned
        self.OwnedQuerySet = OwnedQuerySet
        self.post_save = post_save
        self.pre_save = pre_save

    def resolve_model(self, model):
        '''
        Resolve a model given a name or dict with `class` entry.

        :raises ValueError: model specification is wrong or does not exists
        '''
        if not model:
            raise ValueError('Unsupported model specifications')
        if isinstance(model, basestring):
            classname = model
        elif isinstance(model, dict) and 'class' in model:
            classname = model['class']
        else:
            raise ValueError('Unsupported model specifications')

        try:
            return get_document(classname)
        except self.NotRegistered:
            message = '{0} does not exists'.format(classname)
            raise ValueError(message)


db = UDataMongoEngine()
session_interface = MongoEngineSessionInterface(db)


# Load all core models and mixins
from udata.core.spatial.models import *  # noqa
from udata.core.metrics.models import *  # noqa
from udata.core.issues.models import *  # noqa
from udata.core.badges.models import *  # noqa
from udata.core.discussions.models import *  # noqa
from udata.core.followers.models import *  # noqa
from udata.core.user.models import *  # noqa
from udata.core.organization.models import *  # noqa
from udata.core.site.models import *  # noqa
from udata.core.dataset.models import *  # noqa
from udata.core.reuse.models import *  # noqa
from udata.core.activity.models import *  # noqa
from udata.core.topic.models import *  # noqa
from udata.core.post.models import *  # noqa
from udata.core.jobs.models import *  # noqa

from udata.features.transfer.models import *  # noqa
from udata.features.territories.models import *  # noqa


def init_app(app):
    # use `{database_name}-test` database for testing
    if app.config['TESTING']:
        parsed_url = urlparse(app.config['MONGODB_HOST'])
        parsed_url = parsed_url._replace(path='%s-test' % parsed_url.path)
        app.config['MONGODB_HOST'] = parsed_url.geturl()
    db.init_app(app)
    for plugin in app.config['PLUGINS']:
        name = 'udata_{0}.models'.format(plugin)
        try:
            importlib.import_module(name)
        except ImportError as e:
            log.warning('Error importing %s: %s', name, e)
        except Exception as e:
            log.error('Error during import of %s: %s', name, e)
