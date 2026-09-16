import logging

from mongoengine import EmbeddedDocument
from mongoengine.fields import GenericReferenceField

from udata.api_fields import field, generate_fields
from udata.core.dataservices.models import Dataservice
from udata.core.dataset.models import Dataset
from udata.core.organization.models import Organization
from udata.core.reuse.models import Reuse
from udata.core.user.models import User
from udata.features.notifications.actions import notifier
from udata.features.notifications.constants import NotificationType
from udata.features.notifications.events import NotificationEvent
from udata.models import Transfer

log = logging.getLogger(__name__)


@generate_fields()
class TransferRequestNotificationDetails(EmbeddedDocument):
    transfer_owner = field(
        GenericReferenceField(choices=(User, Organization), required=True),
        readonly=True,
        auditable=False,
        allow_null=True,
        filterable={},
    )
    transfer_recipient = field(
        GenericReferenceField(choices=(User, Organization), required=True),
        readonly=True,
        auditable=False,
        allow_null=True,
        filterable={},
    )
    transfer_subject = field(
        GenericReferenceField(choices=(Dataset, Dataservice, Reuse), required=True),
        readonly=True,
        auditable=False,
        allow_null=True,
        filterable={},
    )


class TransferRequested(NotificationEvent):
    type = NotificationType.TRANSFER_REQUESTED

    def __init__(self, transfer: Transfer):
        self.transfer = transfer

    @property
    def occurred_at(self):
        return self.transfer.created

    def recipients(self):
        recipient = self.transfer.recipient
        if isinstance(recipient, User):
            return [recipient]
        if isinstance(recipient, Organization):
            return [member.user for member in recipient.by_role("admin")]
        return []

    def _subject(self):
        return {
            "transfer_owner": self.transfer.owner,
            "transfer_recipient": self.transfer.recipient,
            "transfer_subject": self.transfer.subject,
        }

    def via_app(self, recipient):
        if self.already_pending(recipient, **self._subject()):
            return None
        return TransferRequestNotificationDetails(**self._subject())


@Transfer.on_create.connect
def on_transfer_created(transfer, **kwargs):
    TransferRequested(transfer).dispatch()


@Transfer.after_handle.connect
def on_handle_transfer(transfer, **kwargs):
    """Update handled_at timestamp on related notifications when a transfer is handled"""
    from udata.features.notifications.models import Notification

    Notification.objects(
        details__transfer_subject=transfer.subject,
        details__transfer_owner=transfer.owner,
        details__transfer_recipient=transfer.recipient,
        handled_at=None,
    ).mark_handled()


@notifier("transfer_request")
def transfer_request_notifications(user):
    """Notify user about pending transfer requests"""
    orgs = [o for o in user.organizations if o.is_member(user)]
    notifications = []

    qs = Transfer.objects(recipient__in=[user] + orgs, status="pending")
    # Only fetch required fields for notification serialization
    # Greatly improve performances and memory usage
    qs = qs.only("id", "created", "subject")

    # Do not dereference subject (so it's a DBRef)
    # Also improve performances and memory usage
    for transfer in qs.no_dereference():
        notifications.append(
            (
                transfer.created,
                {
                    "id": transfer.id,
                    "subject": {
                        "class": transfer.subject["_cls"].lower(),
                        "id": transfer.subject["_ref"].id,
                    },
                },
            )
        )

    return notifications


@Transfer.after_delete.connect
def on_transfer_deleted(transfer, **kwargs):
    """Clean up notifications when a transfer is deleted"""
    from udata.features.notifications.models import Notification

    try:
        # Delete all notifications that reference this transfer
        Notification.objects(
            details__transfer_owner=transfer.owner,
            details__transfer_recipient=transfer.recipient,
            details__transfer_subject=transfer.subject,
        ).delete()
    except Exception as e:
        log.error(f"Error cleaning up notifications for deleted transfer {transfer.id}: {e}")
