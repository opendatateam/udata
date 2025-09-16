import logging
from datetime import datetime

from blinker import Signal
from flask import g
from mongoengine.errors import DoesNotExist
from mongoengine.signals import post_save

from udata.api_fields import get_fields
from udata.auth import current_user
from udata.mongo import db
from udata.utils import get_field_value_from_path

from .signals import new_activity

__all__ = ("Activity",)

log = logging.getLogger(__name__)


_registered_activities = {}


class EmitNewActivityMetaClass(db.BaseDocumentMetaclass):
    """Ensure any child class dispatches the on_new signal"""

    def __new__(cls, name, bases, attrs):
        new_class = super(EmitNewActivityMetaClass, cls).__new__(cls, name, bases, attrs)
        if new_class.key:
            post_save.connect(cls.post_save, sender=new_class)
            _registered_activities[new_class.key] = new_class
        return new_class

    @classmethod
    def post_save(cls, sender, document, **kwargs):
        sender.on_new.send(sender, activity=document)


class Activity(db.Document, metaclass=EmitNewActivityMetaClass):
    """Store the activity entries for a single related object"""

    actor = db.ReferenceField("User", required=True)
    organization = db.ReferenceField("Organization")
    related_to = db.ReferenceField(db.DomainModel, required=True)
    created_at = db.DateTimeField(default=datetime.utcnow, required=True)
    changes = db.ListField(db.StringField())

    extras = db.ExtrasField()

    on_new = Signal()

    meta = {
        "indexes": [
            "actor",
            "organization",
            "related_to",
            "-created_at",
            ("actor", "-created_at"),
            ("organization", "-created_at"),
            ("related_to", "-created_at"),
        ],
        "allow_inheritance": True,
    }

    key = None
    label = None
    badge_type = "primary"
    icon = "fa fa-info-circle"
    template = "activity/base.html"

    @classmethod
    def connect(cls, func):
        return cls.on_new.connect(func, sender=cls)

    @classmethod
    def emit(cls, related_to, organization=None, changed_fields=None, extras=None):
        if hasattr(g, "harvest_activity_user"):
            # We're in the context of a harvest action with a harvest activity user to use as actor
            actor = g.harvest_activity_user
        else:
            actor = current_user._get_current_object()
        new_activity.send(
            cls,
            related_to=related_to,
            actor=actor,
            organization=organization,
            changes=changed_fields,
            extras=extras,
        )


class Auditable(object):
    def clean(self, **kwargs):
        super().clean()
        """
        Fetch original document changed fields values before the new one erase it.
        """
        changed_fields = self._get_changed_fields()
        if changed_fields:
            try:
                # `only` does not support having nested list as expressed in changed fields, ex resources.0.title
                # thus we only strip to direct attributes for simplicity
                direct_attributes = set(field.split(".")[0] for field in changed_fields)
                old_document = self.__class__.objects.only(*direct_attributes).get(pk=self.pk)
                self._previous_changed_fields = {}
                for field_path in changed_fields:
                    field_value = get_field_value_from_path(old_document, field_path)
                    self._previous_changed_fields[field_path] = field_value
            except DoesNotExist:
                pass

    @classmethod
    def post_save(cls, sender, document, **kwargs):
        try:
            auditable_fields = [
                key for key, field, info in get_fields(cls) if info.get("auditable", True)
            ]
        except Exception:
            # for backward compatibility, all fields are treated as auditable for classes not using field() function
            auditable_fields = document._get_changed_fields()
        changed_fields = [
            field
            for field in document._get_changed_fields()
            if field.split(".")[0] in auditable_fields
        ]
        if "post_save" in kwargs.get("ignores", []):
            return
        cls.after_save.send(document)
        if kwargs.get("created"):
            cls.on_create.send(document)
        elif len(changed_fields):
            previous = getattr(document, "_previous_changed_fields", None)
            # make sure that changed fields have actually changed when comparing the document
            # once it has been reloaded. It may have been cleaned or normalized when saved to mongo.
            # We compare them one by one with the previous value stored in _previous_changed_fields.
            # See https://github.com/opendatateam/udata/pull/3412 for more context.
            document.reload()
            changed_fields = [
                field
                for field in changed_fields
                if previous[field] != get_field_value_from_path(document, field)
            ]
            if changed_fields:
                cls.on_update.send(document, changed_fields=changed_fields, previous=previous)
        if getattr(document, "deleted_at", None) or getattr(document, "deleted", None):
            cls.on_delete.send(document)
