import logging

from mongoengine import EmbeddedDocument
from mongoengine.fields import ReferenceField

from udata.api_fields import field, generate_fields
from udata.core.dataset.api_fields import dataset_fields
from udata.core.dataset.models import Dataset
from udata.core.owned import get_responsible_users
from udata.core.reuse.models import Reuse
from udata.features.notifications.constants import NotificationType
from udata.features.notifications.events import NotificationEvent

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
        nested_fields=dataset_fields,
        auditable=False,
        allow_null=True,
        filterable={},
    )


class ReuseCreated(NotificationEvent):
    """One event per reused dataset: each set of dataset owners hears about their own."""

    type = NotificationType.REUSE_CREATED

    def __init__(self, reuse: Reuse, dataset: Dataset):
        self.reuse = reuse
        self.dataset = dataset

    @property
    def occurred_at(self):
        return self.reuse.created_at

    def recipients(self):
        return [user for user in get_responsible_users(self.dataset) if user]

    def via_app(self, recipient):
        return ReuseCreatedNotificationDetails(reuse=self.reuse, dataset=self.dataset)


@Reuse.on_create.connect
def on_reuse_created(reuse, **kwargs):
    for dataset in reuse.datasets:
        ReuseCreated(reuse, dataset).dispatch()


@Reuse.on_delete.connect
def cleanup_reuse_notifications(reuse, **kwargs):
    """Clean up notifications when a reuse is deleted"""
    from udata.features.notifications.models import Notification

    try:
        Notification.objects(details__reuse=reuse).delete()
    except Exception as e:
        log.error(f"Error cleaning up notifications for deleted reuse {reuse.id}: {e}")
