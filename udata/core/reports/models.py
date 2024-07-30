from datetime import datetime

from bson import DBRef
from mongoengine import DO_NOTHING, NULLIFY, signals

from udata.api_fields import field, function_field, generate_fields
from udata.core.user.api_fields import user_ref_fields
from udata.core.user.models import User
from udata.mongo import db
from udata.uris import endpoint_for

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

    # Here we use the lazy version of `GenericReferenceField` because we could point to a
    # non existant model (if it was deleted we want to keep the report data).
    subject = field(
        db.GenericLazyReferenceField(reverse_delete_rule=DO_NOTHING, choices=REPORTABLE_MODELS)
    )

    subject_deleted_at = field(
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

    @function_field(description="Link to the API endpoint for this report")
    def self_api_url(self):
        return endpoint_for("api.report", report=self, _external=True)

    @classmethod
    def mark_as_deleted_soft_delete(cls, sender, document, **kwargs):
        """
        Called when updating a model (maybe updating the `deleted` date)
        Some documents like Discussion do not have a `deleted` attribute.
        """
        if hasattr(document, "deleted") and document.deleted:
            Report.objects(subject=document, subject_deleted_at=None).update(
                subject_deleted_at=datetime.utcnow
            )

    @classmethod
    def mark_as_deleted_hard_delete(cls, sender, document, **kwargs):
        """
        Call when really deleting a model from the database.
        """
        # Here we are forced to do a manual `DBRef(sender.__name__.lower(), document.id)`
        # because the document doesn't exist anymore…
        Report.objects(
            subject=DBRef(sender.__name__.lower(), document.id), subject_deleted_at=None
        ).update(subject_deleted_at=datetime.utcnow)


for model in REPORTABLE_MODELS:
    signals.post_save.connect(Report.mark_as_deleted_soft_delete, sender=model)
    signals.post_delete.connect(Report.mark_as_deleted_hard_delete, sender=model)
