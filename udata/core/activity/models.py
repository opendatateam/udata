import logging
from datetime import UTC, datetime

from blinker import Signal
from flask import g
from mongoengine import Q
from mongoengine.base import TopLevelDocumentMetaclass
from mongoengine.fields import (
    DateTimeField,
    GenericReferenceField,
    ListField,
    ReferenceField,
    StringField,
)
from mongoengine.signals import post_save

from udata.api import api
from udata.api_fields import field, generate_fields
from udata.auth import current_user
from udata.core.organization.models import Organization
from udata.core.user.models import User
from udata.mongo.document import DomainModel
from udata.mongo.document import UDataDocument as Document
from udata.mongo.extras_fields import ExtrasField

from .signals import new_activity

__all__ = ("Activity",)

log = logging.getLogger(__name__)


_registered_activities = {}

# Who an activity can be attributed to. Declared by class name rather than by class:
# `HarvestSource` and `ApiToken` live in modules that import the activity machinery
# back, and a `GenericReferenceField` resolves the names from the document registry.
ACTOR_TYPES = ("User", "HarvestSource", "ApiToken")


class EmitNewActivityMetaClass(TopLevelDocumentMetaclass):
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


def filter_by_user(base_query, value):
    """Keep the activities of one actor, designated by user id.

    `actor` is a generic reference, matched on the whole `{_cls, _ref}` sub-document
    mongoengine builds from a document: an id alone does not say which collection it
    points at. An unknown id resolves to no actor, which matches no activity.
    """
    return base_query.filter(actor=User.objects(id=value).first())


def filter_by_organization(base_query, value):
    """Keep what an organization did, and what was done to it."""
    return base_query.filter(Q(organization=value) | Q(related_to=value))


def filter_by_keys(base_query, values):
    """Keep the given activity kinds, e.g. only the edits.

    The keys cannot be declared as parser `choices`: the subclasses that carry them
    register themselves after this class is built.
    """
    unknown = set(values) - set(_registered_activities)
    if unknown:
        api.abort(400, "Unknown activity key(s): {0}".format(", ".join(sorted(unknown))))

    # `_cls` is what the key is stored as, and it leads every index of the collection.
    return base_query.filter(
        __raw__={"_cls": {"$in": [_registered_activities[key]._class_name for key in values]}}
    )


@generate_fields(
    default_sort="-created_at",
    standalone_filters=[
        {
            "key": "user",
            "type": str,
            "constraints": ["objectid"],
            "query": filter_by_user,
            "help": "Filter activities for that particular user",
        },
        {
            "key": "organization",
            "type": str,
            "constraints": ["objectid"],
            "query": filter_by_organization,
            "help": "Filter activities for that particular organization",
        },
        {
            "key": "related_to",
            "type": str,
            "constraints": ["objectid"],
            "query": lambda base_query, value: base_query.filter(related_to=value),
            "help": "Filter activities for that particular object id (ex : reuse, dataset, etc.)",
        },
        {
            "key": "key",
            "type": str,
            "is_list": True,
            "query": filter_by_keys,
            "help": "Filter activities on those keys (ex : dataset:updated). Repeatable.",
        },
    ],
)
class Activity(Document, metaclass=EmitNewActivityMetaClass):
    """Store the activity entries for a single related object"""

    # Every field is read-only: activities are emitted by signals, never written through
    # the API.
    actor = field(
        GenericReferenceField(choices=ACTOR_TYPES, required=True),
        readonly=True,
        description="Who performed the action",
    )
    organization = field(
        ReferenceField(Organization),
        readonly=True,
        allow_null=True,
        description="The organization who performed the action",
    )
    # Serialized as the target's `str()`, its title in practice. `DomainModel` is a bare
    # placeholder; the concrete target type is declared by each subclass, and read
    # alongside as `related_to_kind` / `related_to_id` / `related_to_url`.
    related_to = field(
        ReferenceField(DomainModel, required=True),
        readonly=True,
        description="The activity target name",
    )
    created_at = field(
        DateTimeField(default=lambda: datetime.now(UTC), required=True),
        readonly=True,
        sortable=True,
        description="When the action has been performed",
    )
    changes = field(
        ListField(StringField()),
        readonly=True,
        description="Changed attributes as list",
    )

    extras = field(ExtrasField(), readonly=True, description="Extras attributes as key-value pairs")

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

    # `key`, `label` and `icon` are class attributes each subclass overrides, which
    # `generate_fields` cannot see: it only picks up mongo fields and callables. Hence
    # these accessors, renamed to keep the attribute name on the API.
    @field(description="The key of the activity", rename="key")
    def activity_key(self) -> str:
        return self.key

    @field(description="The label of the activity", rename="label")
    def activity_label(self) -> str:
        return self.label

    @field(description="The icon of the activity", rename="icon")
    def activity_icon(self) -> str:
        return self.icon

    @field(description="The activity target object identifier")
    def related_to_id(self) -> str:
        return str(self.related_to.id)

    @field(description="The activity target object class name")
    def related_to_kind(self) -> str:
        return self.related_to.__class__.__name__

    @field(description="The activity target url")
    def related_to_url(self) -> str:
        return self.related_to.url_for()

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
