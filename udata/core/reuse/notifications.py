import logging

from mongoengine import EmbeddedDocument
from mongoengine.fields import ReferenceField

from udata.api_fields import field, generate_fields
from udata.core.dataset.api_fields import dataset_fields
from udata.core.dataset.models import Dataset
from udata.core.owned import get_responsible_users
from udata.core.reuse.models import Reuse

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


@Reuse.on_create.connect
def on_reuse_created(reuse):
    """Create notifications when a reuse is created"""
    from udata.features.notifications.models import Notification

    if not reuse.datasets:
        return
    for dataset in reuse.datasets:
        for owner in get_responsible_users(dataset):
            if owner:
                notification = Notification(
                    user=owner,
                    details=ReuseCreatedNotificationDetails(
                        reuse=reuse,
                        dataset=dataset,
                    ),
                )
                notification.created_at = reuse.created_at
                notification.save()


@Reuse.on_delete.connect
def cleanup_reuse_notifications(reuse, **kwargs):
    """Clean up notifications when a reuse is deleted"""
    from udata.features.notifications.models import Notification

    try:
        Notification.objects(details__reuse=reuse).delete()
    except Exception as e:
        log.error(f"Error cleaning up notifications for deleted reuse {reuse.id}: {e}")
