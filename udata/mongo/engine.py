from bson import DBRef, ObjectId
from flask_mongoengine import MongoEngine, MongoEngineSessionInterface
from flask_storage.mongo import FileField, ImageField
from mongoengine.base import TopLevelDocumentMetaclass, get_document
from mongoengine.errors import ValidationError
from mongoengine.signals import post_save, pre_save

from .badges_field import BadgesField
from .datetime_fields import DateField, DateRange, Datetimed
from .document import DomainModel, UDataDocument
from .extras_fields import ExtrasField, OrganizationExtrasField
from .queryset import UDataQuerySet
from .slug_fields import SlugField
from .taglist_field import TagListField
from .url_field import URLField
from .uuid_fields import AutoUUIDField


class UDataMongoEngine(MongoEngine):
    """Customized mongoengine with extra fields types and helpers"""

    def __init__(self, app=None):
        super(UDataMongoEngine, self).__init__(app)
        self.BadgesField = BadgesField
        self.TagListField = TagListField
        self.DateField = DateField
        self.Datetimed = Datetimed
        self.ExtrasField = ExtrasField
        self.OrganizationExtrasField = OrganizationExtrasField
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
        self.post_save = post_save
        self.pre_save = pre_save

    def resolve_model(self, model):
        """
        Resolve a model given a name or dict with `class` entry.

        :raises ValueError: model specification is wrong or does not exists
        """
        if not model:
            raise ValueError("Unsupported model specifications")
        if isinstance(model, str):
            classname = model
        elif isinstance(model, dict) and "class" in model:
            classname = model["class"]
        else:
            raise ValueError("Unsupported model specifications")

        try:
            return get_document(classname)
        except self.NotRegistered:
            message = 'Model "{0}" does not exist'.format(classname)
            raise ValueError(message)


db = UDataMongoEngine()
session_interface = MongoEngineSessionInterface(db)
