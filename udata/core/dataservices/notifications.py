import logging

from mongoengine import EmbeddedDocument
from mongoengine.fields import ReferenceField

from udata.api_fields import field, generate_fields
from udata.core.dataservices.models import Dataservice
from udata.core.dataset.api_fields import dataset_fields
from udata.core.dataset.models import Dataset
from udata.core.owned import get_responsible_users

log = logging.getLogger(__name__)


@generate_fields()
class DataserviceCreatedNotificationDetails(EmbeddedDocument):
    dataservice = field(
        ReferenceField(Dataservice),
        readonly=True,
        nested_fields=Dataservice.__ref_fields__,
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


@Dataservice.on_create.connect
def on_dataservice_created(dataservice):
    """Create notifications when a dataservice is created"""
    from udata.features.notifications.models import Notification

    if not dataservice.datasets:
        return
    for dataset in dataservice.datasets:
        for owner in get_responsible_users(dataset):
            if owner:
                notification = Notification(
                    user=owner,
                    details=DataserviceCreatedNotificationDetails(
                        dataservice=dataservice,
                        dataset=dataset,
                    ),
                )
                notification.created_at = dataservice.created_at
                notification.save()


@Dataservice.on_delete.connect
def cleanup_dataservice_notifications(dataservice, **kwargs):
    """Clean up notifications when a dataservice is deleted"""
    from udata.features.notifications.models import Notification
    
    try:
        Notification.objects(details__dataservice=dataservice).delete()
    except Exception as e:
        log.error(f"Error cleaning up notifications for deleted dataservice {dataservice.id}: {e}")
