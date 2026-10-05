import logging
from datetime import UTC, datetime

from mongoengine import EmbeddedDocument
from mongoengine.fields import ReferenceField

from udata.api_fields import field, generate_fields
from udata.core.dataset.api_fields import dataset_ref_fields
from udata.core.dataset.models import Dataset
from udata.core.dataset.notifications import DatasetReusedEvent
from udata.core.reuse.models import Reuse
from udata.features.notifications.constants import NotificationType

log = logging.getLogger(__name__)


@generate_fields()
class ReuseCreatedNotificationDetails(EmbeddedDocument):
    reuse = field(
        ReferenceField(Reuse),
        readonly=True,
        nested_fields=Reuse.__ref_fields__,
        auditable=False,
        allow_null=True,
        filterable={},
    )
    dataset = field(
        ReferenceField(Dataset),
        readonly=True,
        nested_fields=dataset_ref_fields,
        auditable=False,
        allow_null=True,
        filterable={},
    )


class ReuseCreated(DatasetReusedEvent):
    """A reuse became visible: one event per reused dataset, so that each set of
    dataset owners hears about their own."""

    type = NotificationType.REUSE_CREATED

    def __init__(self, reuse: Reuse, dataset: Dataset, occurred_at: datetime):
        self.reuse = reuse
        self.dataset = dataset
        self._occurred_at = occurred_at

    @property
    def occurred_at(self):
        return self._occurred_at

    def via_app(self, recipient):
        return ReuseCreatedNotificationDetails(reuse=self.reuse, dataset=self.dataset)


def announce_reuse(reuse: Reuse, occurred_at: datetime) -> None:
    for dataset in reuse.datasets:
        ReuseCreated(reuse, dataset, occurred_at).dispatch()


# A private reuse is announced when it is published, not when it is created: until
# then, its existence is its owner's business only.
@Reuse.on_create.connect
def on_reuse_created(reuse, **kwargs):
    if not reuse.private:
        announce_reuse(reuse, reuse.created_at)


@Reuse.on_update.connect
def on_reuse_published(reuse, changed_fields, previous, **kwargs):
    if "private" in changed_fields and previous.get("private") and not reuse.private:
        announce_reuse(reuse, datetime.now(UTC))


@Reuse.on_delete.connect
def cleanup_reuse_notifications(reuse, **kwargs):
    """Clean up notifications when a reuse is deleted"""
    from udata.features.notifications.models import Notification

    try:
        Notification.objects(details__reuse=reuse).delete()
    except Exception as e:
        log.error(f"Error cleaning up notifications for deleted reuse {reuse.id}: {e}")
