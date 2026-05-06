import logging
from collections import OrderedDict
from datetime import UTC, datetime
from urllib.parse import urlparse

from flask import url_for
from mongoengine import CASCADE, NULLIFY, EmbeddedDocument
from mongoengine.fields import (
    BooleanField,
    DateTimeField,
    DictField,
    EmbeddedDocumentField,
    ListField,
    ReferenceField,
    StringField,
)
from werkzeug.utils import cached_property

from udata.api import fields
from udata.api_fields import field, generate_fields, required_if
from udata.auth import admin_permission
from udata.core.dataservices.models import Dataservice
from udata.core.dataservices.models import HarvestMetadata as HarvestDataserviceMetadata
from udata.core.dataset.models import HarvestDatasetMetadata
from udata.core.owned import Owned, OwnedQuerySet
from udata.i18n import lazy_gettext as _
from udata.models import Dataset
from udata.mongo.document import UDataDocument as Document
from udata.mongo.slug_fields import SlugField

from .api_fields import source_permissions_fields

log = logging.getLogger(__name__)

HARVEST_FREQUENCIES = OrderedDict(
    (
        ("manual", _("Manual")),
        ("monthly", _("Monthly")),
        ("weekly", _("Weekly")),
        ("daily", _("Daily")),
    )
)

HARVEST_JOB_STATUS = OrderedDict(
    (
        ("pending", _("Pending")),
        ("initializing", _("Initializing")),
        ("initialized", _("Initialized")),
        ("processing", _("Processing")),
        ("done", _("Done")),
        ("done-errors", _("Done with errors")),
        ("failed", _("Failed")),
    )
)

HARVEST_ITEM_STATUS = OrderedDict(
    (
        ("pending", _("Pending")),
        ("started", _("Started")),
        ("done", _("Done")),
        ("failed", _("Failed")),
        ("skipped", _("Skipped")),
        ("archived", _("Archived")),
    )
)

DEFAULT_HARVEST_FREQUENCY = "manual"
DEFAULT_HARVEST_JOB_STATUS = "pending"
DEFAULT_HARVEST_ITEM_STATUS = "pending"


@generate_fields()
class HarvestError(EmbeddedDocument):
    """Store harvesting errors"""

    created_at = field(
        DateTimeField(default=lambda: datetime.now(UTC), required=True),
        readonly=True,
        description="The error creation date",
    )
    message = field(StringField(), description="The error short message")
    details = field(
        StringField(),
        readonly=True,
        attribute=lambda o: o.details if admin_permission.can() else None,
        description="Optional details (only for super-admins)",
    )


@generate_fields()
class HarvestLog(EmbeddedDocument):
    level = field(StringField(required=True))
    message = field(StringField(required=True))


@generate_fields()
class HarvestItem(EmbeddedDocument):
    remote_id = field(StringField(), description="The item remote ID to process")
    remote_url = field(StringField(), description="The item remote url (if available)")
    dataset = field(ReferenceField(Dataset), description="The processed dataset", allow_null=True)
    dataservice = field(
        ReferenceField(Dataservice), description="The processed dataservice", allow_null=True
    )
    status = field(
        StringField(
            choices=list(HARVEST_ITEM_STATUS),
            default=DEFAULT_HARVEST_ITEM_STATUS,
            required=True,
        ),
        description="The item status",
    )
    created = field(
        DateTimeField(default=lambda: datetime.now(UTC), required=True),
        readonly=True,
        description="The item creation date",
    )
    started = field(DateTimeField(), description="The item start date")
    ended = field(DateTimeField(), description="The item end date")
    errors = field(ListField(EmbeddedDocumentField(HarvestError)), description="The item errors")
    logs = field(
        ListField(EmbeddedDocumentField(HarvestLog), default=[]),
        description="The item logs",
    )
    args = field(ListField(StringField()), description="The item positional arguments")
    kwargs = field(DictField(), description="The item keyword arguments")


VALIDATION_ACCEPTED = "accepted"
VALIDATION_REFUSED = "refused"
VALIDATION_PENDING = "pending"

VALIDATION_STATES = {
    VALIDATION_PENDING: _("Pending"),
    VALIDATION_ACCEPTED: _("Accepted"),
    VALIDATION_REFUSED: _("Refused"),
}


@generate_fields()
class HarvestSourceValidation(EmbeddedDocument):
    """Store harvest source validation details"""

    state = field(
        StringField(choices=list(VALIDATION_STATES), default=VALIDATION_PENDING, required=True),
        description="Is it validated or not",
    )
    by = field(
        ReferenceField("User"),
        readonly=True,
        allow_null=True,
        description="Who performed the validation",
    )
    on = field(
        DateTimeField(),
        readonly=True,
        description="Date on which validation was performed",
    )
    comment = field(
        StringField(),
        description="A comment about the validation. Required on rejection",
        checks=[required_if(state=VALIDATION_REFUSED)],
    )


class HarvestSourceQuerySet(OwnedQuerySet):
    def visible(self):
        return self(deleted=None)


@generate_fields(searchable=True)
class HarvestSource(Owned, Document[HarvestSourceQuerySet]):
    name = field(StringField(max_length=255), description="The source display name")
    slug = field(
        SlugField(max_length=255, required=True, unique=True, populate_from="name", update=True),
        readonly=True,
        description="The source permalink string",
    )
    description = field(StringField(), markdown=True, description="The source description")
    url = field(StringField(required=True), description="The source base URL")
    backend = field(
        StringField(required=True),
        description="The source backend",
    )
    config = field(DictField(), description="The configuration as key-value pairs")
    periodic_task = ReferenceField("PeriodicTask", reverse_delete_rule=NULLIFY)
    created_at = field(
        DateTimeField(default=lambda: datetime.now(UTC), required=True),
        readonly=True,
        description="The source creation date",
    )
    frequency = StringField(
        choices=list(HARVEST_FREQUENCIES), default=DEFAULT_HARVEST_FREQUENCY, required=True
    )
    active = field(BooleanField(default=True), description="Is this source active")
    autoarchive = field(
        BooleanField(default=True),
        description=(
            "If enabled, datasets not present on the remote source will be automatically archived"
        ),
    )
    validation = field(
        EmbeddedDocumentField(HarvestSourceValidation, default=HarvestSourceValidation),
        readonly=True,
        description="Has the source been validated",
    )
    deleted = field(DateTimeField(), readonly=True, description="The source deletion date")

    @property
    def domain(self):
        parsed = urlparse(self.url)
        return parsed.netloc.split(":")[0]

    @classmethod
    def get(cls, ident):
        return cls.objects(slug=ident).first() or cls.objects.get(pk=ident)

    def get_last_job(self, reduced=False):
        qs = HarvestJob.objects(source=self)
        if reduced:
            qs = qs.exclude("source", "items", "errors", "data")
            qs = qs.no_dereference()
        return qs.order_by("-created").first()

    # last_job is registered on __read_fields__ after HarvestJob is defined below
    # (circular reference between HarvestSource and HarvestJob)
    @cached_property
    def last_job(self):
        return self.get_last_job(reduced=True)

    @property
    @field(
        description="The source schedule (interval or cron expression)",
        readonly=True,
    )
    def schedule(self):
        if not self.periodic_task:
            return None
        return self.periodic_task.schedule_display

    @property
    @field(nested_fields=source_permissions_fields, readonly=True)
    def permissions(self):
        from .permissions import HarvestSourceAdminPermission, HarvestSourcePermission

        return {
            "edit": HarvestSourceAdminPermission(self),
            "delete": HarvestSourceAdminPermission(self),
            "run": HarvestSourceAdminPermission(self),
            "preview": HarvestSourcePermission(self),
            "validate": admin_permission,
            "schedule": admin_permission,
        }

    meta = {
        "indexes": [
            {
                "fields": ["$name", "$url"],
                "default_language": "french",
                "weights": {"name": 10, "url": 5},
            },
            "-created_at",
            "slug",
            ("deleted", "-created_at"),
        ]
        + Owned.meta["indexes"],
        "ordering": ["-created_at"],
        "queryset_class": HarvestSourceQuerySet,
    }

    def __str__(self):
        return self.name or ""


@generate_fields()
class HarvestJob(Document):
    """Keep track of harvestings"""

    created = field(
        DateTimeField(default=lambda: datetime.now(UTC), required=True),
        readonly=True,
        description="The job creation date",
    )
    started = field(DateTimeField(), readonly=True, description="The job start date")
    ended = field(DateTimeField(), readonly=True, description="The job end date")
    status = field(
        StringField(
            choices=list(HARVEST_JOB_STATUS),
            default=DEFAULT_HARVEST_JOB_STATUS,
            required=True,
        ),
        readonly=True,
        description="The job status",
    )
    errors = field(
        ListField(EmbeddedDocumentField(HarvestError)),
        readonly=True,
        description="The job initialization errors",
    )
    # Items are exposed as a paginated subresource link with status/type counters,
    # to avoid loading thousands of dereferenced items for every job in a list.
    items = field(
        ListField(EmbeddedDocumentField(HarvestItem)),
        readonly=True,
        href=lambda o: url_for("api.harvest_job_items", ident=o.id),
        href_extra=lambda o: {
            "by_status": {
                status: sum(1 for item in o.items if item.status == status)
                for status in HARVEST_ITEM_STATUS
            },
            "by_type": {
                "dataset": sum(1 for item in o.items if item.dataset),
                "dataservice": sum(1 for item in o.items if item.dataservice),
            },
        },
    )
    source = field(
        ReferenceField(HarvestSource, reverse_delete_rule=CASCADE),
        readonly=True,
        description="The source owning the job",
    )
    data = DictField()

    meta = {
        "indexes": [
            "-created",
            "source",
            ("source", "-created"),
            "items.dataset",
            "items.dataservice",
        ],
        "ordering": ["-created"],
    }


HarvestSource.__read_fields__["last_job"] = fields.Nested(
    HarvestJob.__read_fields__,
    description="The last job for this source",
    allow_null=True,
    readonly=True,
)


def archive_harvested_dataset(dataset, reason, dryrun=False):
    """
    Archive an harvested dataset, setting extras accordingly.
    If `dryrun` is True, the dataset is not saved but validated only.
    """
    log.debug("Archiving dataset %s", dataset.id)
    archival_date = datetime.now(UTC)
    dataset.archived = archival_date
    if not dataset.harvest:
        dataset.harvest = HarvestDatasetMetadata()
    dataset.harvest.archived = reason
    dataset.harvest.archived_at = archival_date
    if dryrun:
        dataset.validate()
    else:
        dataset.save()


def archive_harvested_dataservice(dataservice, reason, dryrun=False):
    """
    Archive an harvested dataservice, setting extras accordingly.
    If `dryrun` is True, the dataservice is not saved but validated only.
    """
    log.debug("Archiving dataservice %s", dataservice.id)
    archival_date = datetime.now(UTC)
    dataservice.archived_at = archival_date
    if not dataservice.harvest:
        dataservice.harvest = HarvestDataserviceMetadata()
    dataservice.harvest.archived_reason = reason
    dataservice.harvest.archived_at = archival_date
    if dryrun:
        dataservice.validate()
    else:
        dataservice.save()
