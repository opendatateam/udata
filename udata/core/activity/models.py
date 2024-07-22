from datetime import datetime

from blinker import Signal
from mongoengine.signals import post_save

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
    def emit(cls, related_to, organization=None, extras=None):
        new_activity.send(
            cls,
            related_to=related_to,
            actor=current_user._get_current_object(),
            organization=organization,
            extras=extras,
        )
