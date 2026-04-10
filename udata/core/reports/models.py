from datetime import UTC, datetime

from bson import DBRef
from flask import url_for
from flask_login import current_user
from flask_restx import inputs
from mongoengine import DO_NOTHING, NULLIFY, Q, signals
from mongoengine.fields import (
    DateTimeField,
    DictField,
    GenericLazyReferenceField,
    ReferenceField,
    StringField,
    UUIDField,
)

from udata.api_fields import field, generate_fields
from udata.core.user.api_fields import user_ref_fields
from udata.core.user.models import User
from udata.mongo.document import UDataDocument as Document
from udata.mongo.queryset import UDataQuerySet

from .constants import REPORT_REASONS_CHOICES, REPORTABLE_MODELS


class ReportQuerySet(UDataQuerySet):
    def unhandled(self):
        return self.filter(dismissed_at=None, subject_deleted_at=None)

    def handled(self):
        return self.filter(Q(dismissed_at__ne=None) | Q(subject_deleted_at__ne=None))


SUBJECT_TYPE_CHOICES = [model._class_name for model in REPORTABLE_MODELS]


def filter_by_handled(base_query, filter_value):
    if filter_value is True:
        return base_query.handled()
    elif filter_value is False:
        return base_query.unhandled()
    else:
        return base_query


def filter_by_subject_type(base_query, filter_value):
    return base_query.filter(__raw__={"subject._cls": filter_value})


@generate_fields(
    standalone_filters=[
        {
            "key": "handled",
            "query": filter_by_handled,
            "type": inputs.boolean,
        },
        {
            "key": "subject_type",
            "query": filter_by_subject_type,
            "type": str,
            "choices": SUBJECT_TYPE_CHOICES,
        },
    ],
)
class Report(Document[ReportQuerySet]):
    by = field(
        ReferenceField(User, reverse_delete_rule=NULLIFY),
        nested_fields=user_ref_fields,
        description="Only set if a user was connected when reporting an element.",
        readonly=True,
        allow_null=True,
    )

    # Here we use the lazy version of `GenericReferenceField` because we could point to a
    # non existant model (if it was deleted we want to keep the report data).
    subject = field(
        GenericLazyReferenceField(reverse_delete_rule=DO_NOTHING, choices=REPORTABLE_MODELS)
    )

    subject_deleted_at = field(
        DateTimeField(),
        allow_null=True,
        readonly=True,
    )
    subject_deleted_by = field(
        ReferenceField(User, reverse_delete_rule=NULLIFY),
        nested_fields=user_ref_fields,
        allow_null=True,
        readonly=True,
    )
    subject_label = field(
        StringField(),
        allow_null=True,
        readonly=True,
        description="Title or slug of the subject, saved at report creation for future reference.",
    )

    reason = field(
        StringField(choices=REPORT_REASONS_CHOICES, required=True),
    )
    message = field(
        StringField(),
    )

    reported_at = field(
        DateTimeField(default=lambda: datetime.now(UTC), required=True),
        readonly=True,
        sortable=True,
    )

    dismissed_at = field(
        DateTimeField(),
    )
    dismissed_by = field(
        ReferenceField(User, reverse_delete_rule=NULLIFY),
        nested_fields=user_ref_fields,
        allow_null=True,
    )

    subject_embed_id = field(
        UUIDField(),
        allow_null=True,
        description="UUID of the embedded document within the subject (e.g., a Message within a Discussion)",
    )

    # Callbacks to execute when report is dismissed (for auto-spam reports)
    # Format: {"method_name": {"args": [...], "kwargs": {...}}}
    callbacks = field(
        DictField(default=dict),
        readonly=True,
    )

    meta = {
        "queryset_class": ReportQuerySet,
    }

    def clean(self):
        super().clean()
        if not self.subject_label and self.subject:
            subject = self.subject.fetch()
            self.subject_label = (
                getattr(subject, "title", None)
                or getattr(subject, "name", None)
                or getattr(subject, "slug", None)
            )

    @field(description="Link to the API endpoint for this report")
    def self_api_url(self):
        return url_for("api.report", report=self, _external=True)

    @classmethod
    def _deleted_by_user(cls):
        try:
            if current_user and current_user.is_authenticated:
                return current_user._get_current_object()
        except RuntimeError:
            pass
        return None

    @classmethod
    def _build_deletion_update(cls):
        update = {"subject_deleted_at": datetime.now(UTC)}
        user = cls._deleted_by_user()
        if user:
            update["subject_deleted_by"] = user.id
        return update

    @classmethod
    def mark_subject_deleted(cls, subject):
        """Mark all pending reports for this subject as handled."""
        Report.objects(subject=subject, subject_deleted_at=None).update(
            **cls._build_deletion_update()
        )

    @classmethod
    def mark_subject_deleted_by_embed_id(cls, subject, embed_id):
        """Mark pending reports for a specific embedded document as handled."""
        Report.objects(subject=subject, subject_embed_id=embed_id, subject_deleted_at=None).update(
            **cls._build_deletion_update()
        )

    @classmethod
    def mark_as_deleted_soft_delete(cls, sender, document, **kwargs):
        deleted = getattr(document, "deleted", None) or getattr(document, "deleted_at", None)
        if deleted:
            cls.mark_subject_deleted(document)

    @classmethod
    def mark_as_deleted_hard_delete(cls, sender, document, **kwargs):
        update = cls._build_deletion_update()
        Report.objects(
            subject=DBRef(sender.__name__.lower(), document.id), subject_deleted_at=None
        ).update(**update)


for model in REPORTABLE_MODELS:
    signals.post_save.connect(Report.mark_as_deleted_soft_delete, sender=model)
    signals.post_delete.connect(Report.mark_as_deleted_hard_delete, sender=model)
