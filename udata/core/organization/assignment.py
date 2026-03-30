from datetime import datetime

from mongoengine import CASCADE
from mongoengine.signals import post_save

from udata.api_fields import field, generate_fields
from udata.core.owned import Owned
from udata.core.user.api_fields import user_ref_fields
from udata.mongo import db

from .constants import ASSIGNABLE_OBJECT_TYPES


@generate_fields()
class Assignment(db.Document):
    user = field(
        db.ReferenceField("User", required=True, reverse_delete_rule=CASCADE),
        nested_fields=user_ref_fields,
    )
    organization = field(
        db.ReferenceField("Organization", required=True),
        readonly=True,
    )
    subject = field(
        db.GenericReferenceField(choices=ASSIGNABLE_OBJECT_TYPES, required=True),
    )
    created_at = field(db.DateTimeField(default=datetime.utcnow), readonly=True)

    meta = {
        "indexes": [
            {"fields": ["user", "organization"]},
            {"fields": ["user", "subject"], "unique": True},
        ],
    }


def _auto_assign_on_create(sender, document, **kwargs):
    """Auto-assign an owned object to the current user if they are a partial editor."""
    if not kwargs.get("created"):
        return
    if not isinstance(document, Owned):
        return
    if document.__class__.__name__ not in ASSIGNABLE_OBJECT_TYPES:
        return

    from udata.auth import current_user

    if not document.organization or not current_user or not current_user.is_authenticated:
        return
    member = document.organization.member(current_user._get_current_object())
    if member and member.role == "partial_editor":
        Assignment(
            user=current_user._get_current_object(),
            organization=document.organization,
            subject=document,
        ).save()


post_save.connect(_auto_assign_on_create)


@Owned.on_owner_change.connect
def clean_assignments_on_owner_change(document, previous):
    """Remove all assignments for an object when its ownership changes (e.g. transfer)."""
    Assignment.objects(subject=document).delete()
