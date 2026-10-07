import logging

from mongoengine import EmbeddedDocument
from mongoengine.fields import GenericReferenceField
from mongoengine.signals import post_delete

from udata.api_fields import field, generate_fields
from udata.core.organization.models import Organization
from udata.core.user.models import User
from udata.features.notifications.constants import NotificationType
from udata.features.notifications.events import NotificationEvent, Recipient
from udata.models import Transfer

from .models import TRANSFER_PERSONS, TRANSFERABLE_SUBJECTS

log = logging.getLogger(__name__)


@generate_fields()
class TransferRequestNotificationDetails(EmbeddedDocument):
    types = frozenset({NotificationType.TRANSFER_REQUESTED})

    # Same choices as `Transfer` itself: a notification describes a transfer, so anything
    # transferable must be notifiable. Listing them again here silently dropped the
    # notification of every transfer of a class added on one side only.
    transfer_owner = field(
        GenericReferenceField(choices=TRANSFER_PERSONS, required=True),
        readonly=True,
        auditable=False,
        allow_null=True,
        filterable={},
    )
    transfer_recipient = field(
        GenericReferenceField(choices=TRANSFER_PERSONS, required=True),
        readonly=True,
        auditable=False,
        allow_null=True,
        filterable={},
    )
    transfer_subject = field(
        GenericReferenceField(choices=TRANSFERABLE_SUBJECTS, required=True),
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
            return [Recipient.from_member(member) for member in recipient.by_role("admin")]
        return []

    def via_app(self, recipient):
        subject = {
            "transfer_owner": self.transfer.owner,
            "transfer_recipient": self.transfer.recipient,
            "transfer_subject": self.transfer.subject,
        }
        if self.already_pending(recipient, **subject):
            return None
        return TransferRequestNotificationDetails(**subject)


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


# MongoEngine's own signal rather than a custom one: having a receiver makes
# `Transfer.objects(...).delete()` delete document by document, so the purges of the
# transferred objects clean these notifications up too.
@post_delete.connect_via(Transfer)
def on_transfer_deleted(sender, document, **kwargs):
    """Clean up notifications when a transfer is deleted"""
    from udata.features.notifications.models import Notification

    try:
        # Delete all notifications that reference this transfer
        Notification.objects(
            details__transfer_owner=document.owner,
            details__transfer_recipient=document.recipient,
            details__transfer_subject=document.subject,
        ).delete()
    except Exception as e:
        log.error(f"Error cleaning up notifications for deleted transfer {document.id}: {e}")
