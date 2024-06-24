from datetime import datetime
from mongoengine import NULLIFY

from udata.api_fields import field, generate_fields
from udata.core.dataset.models import Dataset
from udata.core.user.models import User
from udata.mongo import db
from udata.core.user.api_fields import user_ref_fields

from .constants import REPORT_REASONS_CHOICES

@generate_fields()
class Report(db.Document):
    by = field(
        db.ReferenceField(User, reverse_delete_rule=NULLIFY),
        nested_fields=user_ref_fields,
        description="Only set if a user was connected when reporting an element.",
        readonly=True,
        allow_null=True,
    )

    object_type = field(
        db.StringField(choices=[Dataset.__name__])
    )
    object_id = field(
        db.ObjectIdField()
    )
    object_deleted_at = field(
        db.DateTimeField(),
        allow_null=True,
        readonly=True,
    )

    reason = field(
        db.StringField(choices=REPORT_REASONS_CHOICES, required=True),
    )
    message = field(
        db.StringField(),
    )

    reported_at = field(
        db.DateTimeField(default=datetime.utcnow, required=True),
        readonly=True,
    )

