from __future__ import annotations

from mongoengine import EmbeddedDocument
from mongoengine.errors import ValidationError
from mongoengine.fields import (
    BooleanField,
    DateTimeField,
    DictField,
    EmbeddedDocumentField,
    IntField,
    ListField,
    StringField,
)

from udata.api_fields import field, generate_fields
from udata.i18n import lazy_gettext as _
from udata.mongo.document import UDataDocument as Document
from udata.tasks import schedulables

__all__ = ("PeriodicTask", "PERIODS")

CRON = "{minute} {hour} {day_of_month} {month_of_year} {day_of_week}"

#: Authorized values for `PeriodicTask.Interval.period`
PERIODS = ("days", "hours", "minutes", "seconds", "microseconds")


@generate_fields()
class PeriodicTask(Document):
    # `celery_mongobeat` reads and writes this collection directly through pymongo,
    # so its name is a contract shared with `CELERY_MONGODB_SCHEDULER_COLLECTION`
    # and cannot be left to MongoEngine's class-name derivation.
    meta = {"collection": "schedules"}

    @generate_fields()
    class Interval(EmbeddedDocument):
        every = field(IntField(min_value=0, default=0, required=True))
        period = field(StringField(choices=PERIODS, required=True))

        @property
        def period_singular(self):
            return self.period[:-1]

        def __str__(self):
            if self.every == 1:
                return _("every {0.period_singular}").format(self)
            return _("every {0.every} {0.period}").format(self)

    @generate_fields()
    class Crontab(EmbeddedDocument):
        minute = field(StringField(default="*", required=True))
        hour = field(StringField(default="*", required=True))
        day_of_week = field(StringField(default="*", required=True))
        day_of_month = field(StringField(default="*", required=True))
        month_of_year = field(StringField(default="*", required=True))

        def __str__(self):
            return CRON.format(**self._data)

        @classmethod
        def parse(cls, cron):
            m, h, d, M, W = cron.split()
            return cls(
                minute=m,
                hour=h,
                day_of_month=d,
                month_of_year=M,
                day_of_week=W,
            )

    name = field(StringField(unique=True, required=True), description="The job unique name")
    description = field(StringField(), description="The job description")
    task = field(
        StringField(required=True),
        description="The task name",
        # Resolved lazily: flask-restx evaluates a callable `enum` when it renders the
        # schema, by which time Celery has registered the jobs — at import time here,
        # `schedulables()` would still be empty.
        enum=lambda: [job.name for job in schedulables()],
    )
    crontab = field(EmbeddedDocumentField(Crontab), allow_null=True)
    interval = field(EmbeddedDocumentField(Interval), allow_null=True)
    args = field(ListField(), description="The job execution arguments")
    kwargs = field(DictField(), description="The job execution keyword arguments")
    enabled = field(BooleanField(default=False), description="Is this job enabled")
    last_run_at = field(DateTimeField(), readonly=True, description="The last job execution date")

    # Written by the beat on every run (`MongoScheduler.save_entry`). Not part of the
    # API, but declared so that loading a document does not raise `FieldDoesNotExist`.
    total_run_count = IntField(min_value=0, default=0)
    run_immediately = BooleanField()

    def clean(self):
        """Ensure the task carries exactly one of an interval or a crontab schedule."""
        if self.interval and self.crontab:
            raise ValidationError("Cannot define both interval and crontab schedule.")
        if not (self.interval or self.crontab):
            raise ValidationError("Must define either interval or crontab schedule.")

    @property
    @field(rename="schedule", readonly=True, description="The schedule display")
    def schedule_display(self) -> str:
        return str(self.interval) if self.interval else str(self.crontab)
