import logging
from datetime import UTC, datetime

from mongoengine import EmbeddedDocument
from mongoengine.fields import ReferenceField

from udata.api_fields import field, generate_fields
from udata.core.dataservices.models import Dataservice
from udata.core.dataset.api_fields import dataset_fields
from udata.core.dataset.models import Dataset
from udata.core.dataset.notifications import DatasetReusedEvent
from udata.features.notifications.constants import NotificationType

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


class DataserviceCreated(DatasetReusedEvent):
    """A dataservice became visible: one event per exposed dataset, so that each set of
    dataset owners hears about their own."""

    type = NotificationType.DATASERVICE_CREATED

    def __init__(self, dataservice: Dataservice, dataset: Dataset, occurred_at: datetime):
        self.dataservice = dataservice
        self.dataset = dataset
        self._occurred_at = occurred_at

    @property
    def occurred_at(self):
        return self._occurred_at

    def via_app(self, recipient):
        return DataserviceCreatedNotificationDetails(
            dataservice=self.dataservice, dataset=self.dataset
        )


def announce_dataservice(dataservice: Dataservice, occurred_at: datetime) -> None:
    for dataset in dataservice.datasets:
        # `Dataservice.datasets` holds lazy references, which compare unequal to the
        # datasets a setting is scoped to: the event needs the document itself.
        DataserviceCreated(dataservice, dataset.fetch(), occurred_at).dispatch()


# A private dataservice is announced when it is published, not when it is created:
# until then, its existence is its owner's business only.
@Dataservice.on_create.connect
def on_dataservice_created(dataservice, **kwargs):
    if not dataservice.private:
        announce_dataservice(dataservice, dataservice.created_at)


@Dataservice.on_update.connect
def on_dataservice_published(dataservice, changed_fields, previous, **kwargs):
    if "private" in changed_fields and previous.get("private") and not dataservice.private:
        announce_dataservice(dataservice, datetime.now(UTC))


@Dataservice.on_delete.connect
def cleanup_dataservice_notifications(dataservice, **kwargs):
    """Clean up notifications when a dataservice is deleted"""
    from udata.features.notifications.models import Notification

    try:
        Notification.objects(details__dataservice=dataservice).delete()
    except Exception as e:
        log.error(f"Error cleaning up notifications for deleted dataservice {dataservice.id}: {e}")


@Dataset.on_delete.connect
def cleanup_dataservice_and_reuse_dataset_notifications(dataset, **kwargs):
    """Clean up dataservice and reuse notifications when a referenced dataset is deleted"""
    from udata.features.notifications.models import Notification

    try:
        Notification.objects(details__dataset=dataset).delete()
    except Exception as e:
        log.error(
            f"Error cleaning up dataservice and reuse notifications for deleted dataset {dataset.id}: {e}"
        )
