from datetime import datetime

from mongoengine import CASCADE

from udata.api_fields import field, generate_fields
from udata.core.user.api_fields import user_ref_fields
from udata.mongo import db


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
        db.GenericReferenceField(choices=["Dataset", "Dataservice", "Reuse"], required=True),
    )
    created_at = field(db.DateTimeField(default=datetime.utcnow), readonly=True)

    meta = {
        "indexes": [
            {"fields": ["user", "organization"]},
            {"fields": ["user", "subject"], "unique": True},
        ],
    }


def auto_assign_if_partial_editor(obj):
    """Auto-assign an object to the current user if they are a partial editor."""
    from udata.auth import current_user

    if not obj.organization or not current_user.is_authenticated:
        return
    member = obj.organization.member(current_user._get_current_object())
    if member and member.role == "partial_editor":
        Assignment(
            user=current_user._get_current_object(),
            organization=obj.organization,
            subject=obj,
        ).save()
