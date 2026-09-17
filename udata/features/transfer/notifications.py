import logging

from mongoengine import EmbeddedDocument
from mongoengine.fields import GenericReferenceField

from udata.api_fields import field, generate_fields
from udata.core.dataservices.models import Dataservice
from udata.core.dataset.models import Dataset
from udata.core.organization.models import Organization
from udata.core.reuse.models import Reuse
from udata.core.user.models import User
from udata.features.notifications.constants import NotificationReason, NotificationType
from udata.features.notifications.events import NotificationEvent, Recipient
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
            # No reason to carry: being the person the transfer targets is what the
            # type already says.
            return [Recipient(recipient)]
        if isinstance(recipient, Organization):
            return [
                Recipient(member.user, frozenset({NotificationReason.ORGANIZATION_ADMIN}))
                for member in recipient.by_role("admin")
            ]
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
