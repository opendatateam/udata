from datetime import datetime

from bson import DBRef
from flask import url_for
from flask_restx import inputs
from mongoengine import DO_NOTHING, NULLIFY, Q, signals

from udata.api_fields import field, generate_fields
from udata.core.user.api_fields import user_ref_fields
from udata.core.user.models import User
from udata.mongo import db

from .constants import REPORT_REASONS_CHOICES, REPORTABLE_MODELS


class ReportQuerySet(db.BaseQuerySet):
    def unhandled(self):
        return self.filter(dismissed_at=None, subject_deleted_at=None)

    def handled(self):
        return self.filter(Q(dismissed_at__ne=None) | Q(subject_deleted_at__ne=None))


def filter_by_handled(base_query, filter_value):
    if filter_value is True:
        return base_query.handled()
    elif filter_value is False:
        return base_query.unhandled()
    else:
        return base_query


@generate_fields(
    standalone_filters=[
        {
            "key": "handled",
            "query": filter_by_handled,
            "type": inputs.boolean,
        },
    ],
)
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
        sortable=True,
    )

    dismissed_at = field(
        db.DateTimeField(),
    )
    dismissed_by = field(
        db.ReferenceField(User, reverse_delete_rule=NULLIFY),
        nested_fields=user_ref_fields,
        allow_null=True,
    )

    meta = {
        "queryset_class": ReportQuerySet,
    }

    @field(description="Link to the API endpoint for this report")
    def self_api_url(self):
        return url_for("api.report", report=self, _external=True)

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
