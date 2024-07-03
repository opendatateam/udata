from datetime import datetime
from mongoengine import signals, NULLIFY

from udata.api_fields import field, generate_fields
from udata.core.dataset.models import Dataset
from udata.core.user.models import User
from udata.mongo import db
from udata.core.user.api_fields import user_ref_fields

from .constants import REPORT_REASONS_CHOICES, REPORTABLE_MODELS

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
        db.StringField(choices=[m.__name__ for m in REPORTABLE_MODELS])
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

    @classmethod
    def mark_as_deleted_soft_delete(cls, sender, document, **kwargs):
        if document.deleted:
            Report.objects(object_type=sender.__name__, object_id=document.id, object_deleted_at=None).update(object_deleted_at=datetime.utcnow)
    
    def mark_as_deleted_hard_delete(cls, document, **kwargs):
        Report.objects(object_type=document.__class__.__name__, object_id=document.id, object_deleted_at=None).update(object_deleted_at=datetime.utcnow)


for model in REPORTABLE_MODELS:
    signals.post_save.connect(Report.mark_as_deleted_soft_delete, sender=model)
    signals.post_delete.connect(Report.mark_as_deleted_hard_delete, sender=model)