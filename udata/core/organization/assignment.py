from datetime import datetime

from udata.api_fields import field, generate_fields
from udata.core.user.api_fields import user_ref_fields
from udata.mongo import db

ASSIGNABLE_OBJECT_TYPES = ["dataset", "dataservice", "reuse"]


@generate_fields()
class Assignment(db.Document):
    user = field(
        db.ReferenceField("User", required=True),
        nested_fields=user_ref_fields,
    )
    organization = field(
        db.ReferenceField("Organization", required=True),
        readonly=True,
    )
    object_type = field(db.StringField(required=True, choices=ASSIGNABLE_OBJECT_TYPES))
    object_id = field(db.ObjectIdField(required=True))
    created_at = field(db.DateTimeField(default=datetime.utcnow), readonly=True)

    meta = {
        "indexes": [
            {"fields": ["user", "organization"]},
            {"fields": ["user", "object_type", "object_id"], "unique": True},
        ],
    }

    @classmethod
    def has_assignment(cls, user, organization, obj):
        return (
            cls.objects(
                user=user,
                organization=organization,
                object_type=obj.__class__.__name__.lower(),
                object_id=obj.id,
            ).count()
            > 0
        )
