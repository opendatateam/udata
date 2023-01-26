import importlib
import logging
import warnings

from urllib.parse import urlparse

from bson import ObjectId, DBRef
from flask_mongoengine import MongoEngine, MongoEngineSessionInterface
from mongoengine.base import TopLevelDocumentMetaclass, get_document
from mongoengine.errors import ValidationError
from mongoengine.signals import pre_save, post_save

from flask_fs.mongo import FileField, ImageField

from udata import entrypoints
from udata.errors import ConfigError

from .badges_field import BadgesField
from .taglist_field import TagListField
from .datetime_fields import DateField, DateRange, Datetimed
from .extras_fields import ExtrasField
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
        if isinstance(model, str):
            classname = model
        elif isinstance(model, dict) and 'class' in model:
            classname = model['class']
        else:
            raise ValueError('Unsupported model specifications')

        try:
            return get_document(classname)
        except self.NotRegistered:
            message = 'Model "{0}" does not exist'.format(classname)
            raise ValueError(message)


db = UDataMongoEngine()
session_interface = MongoEngineSessionInterface(db)


# Load all core models and mixins
from udata.core.spatial.models import *  # noqa
from udata.core.metrics.models import *  # noqa
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
from udata.core.tags.models import *  # noqa

from udata.features.transfer.models import *  # noqa
from udata.features.territories.models import *  # noqa

# Load HarvestSource model as harvest for catalog
from udata.harvest.models import HarvestSource as Harvest  # noqa

import udata.linkchecker.models  # noqa


MONGODB_DEPRECATED_SETTINGS = 'MONGODB_PORT', 'MONGODB_DB'
MONGODB_DEPRECATED_MSG = '{0} is deprecated, use the MONGODB_HOST url syntax'


def validate_config(config):
    for setting in MONGODB_DEPRECATED_SETTINGS:
        if setting in config:
            msg = MONGODB_DEPRECATED_MSG.format(setting)
            log.warning(msg)
            warnings.warn(msg, category=DeprecationWarning, stacklevel=2)
    url = config['MONGODB_HOST']
    parsed_url = urlparse(url)
    if not all((parsed_url.scheme, parsed_url.netloc)):
        raise ConfigError('{0} is not a valid MongoDB URL'.format(url))
    if len(parsed_url.path) <= 1:
        raise ConfigError('{0} is missing the database path'.format(url))


def build_test_config(config):
    if 'MONGODB_HOST_TEST' in config:
        config['MONGODB_HOST'] = config['MONGODB_HOST_TEST']
    else:
        # use `{database_name}-test` database for testing
        parsed_url = urlparse(config['MONGODB_HOST'])
        parsed_url = parsed_url._replace(path='%s-test' % parsed_url.path)
        config['MONGODB_HOST'] = parsed_url.geturl()
    validate_config(config)


# Avoid nose misdetecting this function as a test
build_test_config.__test__ = False


def init_app(app):
    validate_config(app.config)
    if app.config['TESTING']:
        build_test_config(app.config)
    db.init_app(app)
    entrypoints.get_enabled('udata.models', app)
