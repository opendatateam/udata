from datetime import datetime

from blinker import Signal
from mongoengine.signals import post_save

from udata.api_fields import get_fields
from udata.auth import current_user
from udata.mongo import db

from .signals import new_activity

__all__ = ("Activity",)


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
        new_activity.send(
            cls,
            related_to=related_to,
            actor=current_user._get_current_object(),
            organization=organization,
            changes=changed_fields,
            extras=extras,
        )


class Auditable(object):
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
            field for field in document._get_changed_fields() if field in auditable_fields
        ]
        if "post_save" in kwargs.get("ignores", []):
            return
        cls.after_save.send(document)
        if kwargs.get("created"):
            cls.on_create.send(document)
        elif len(changed_fields):
            cls.on_update.send(document, changed_fields=changed_fields)
        if getattr(document, "deleted_at", None) or getattr(document, "deleted", None):
            cls.on_delete.send(document)
