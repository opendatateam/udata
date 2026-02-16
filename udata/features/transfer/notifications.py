import logging
from datetime import datetime

from mongoengine.fields import GenericReferenceField

from udata.api_fields import field, generate_fields
from udata.core.dataservices.models import Dataservice
from udata.core.dataset.models import Dataset
from udata.core.organization.models import Organization
from udata.core.reuse.models import Reuse
from udata.core.user.models import User
from udata.features.notifications.actions import notifier
from udata.models import Transfer
from udata.mongo import db

log = logging.getLogger(__name__)


@generate_fields()
class TransferRequestNotificationDetails(db.EmbeddedDocument):
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


@Transfer.on_create.connect
def on_transfer_created(transfer, **kwargs):
    """Create notification when a new transfer request is created"""

    from udata.features.notifications.models import Notification

    recipient = transfer.recipient
    owner = transfer.owner
    users = []

    if isinstance(recipient, User):
        users = [recipient]
    elif isinstance(recipient, Organization):
        users = [member.user for member in recipient.members if member.role == "admin"]

    for user in users:
        try:
            # we don't want notifications for the same transfer, if the previous one is stil no handled
            existing = Notification.objects(
                user=user,
                details__transfer_recipient=recipient,
                details__transfer_owner=owner,
                details__transfer_subject=transfer.subject,
                handled_at=None,
            ).first()

            if not existing:
                notification = Notification(
                    user=user,
                    details=TransferRequestNotificationDetails(
                        transfer_owner=owner,
                        transfer_recipient=recipient,
                        transfer_subject=transfer.subject,
                    ),
                )
                notification.created_at = transfer.created
                notification.save()
        except Exception as e:
            log.error(
                f"Error creating notification for admin user {user.id} "
                f"and recipient {recipient.id}: {e}"
            )


@Transfer.after_handle.connect
def on_handle_transfer(transfer, **kwargs):
    """Update handled_at timestamp on related notifications when a transfer is handled"""
    from udata.features.notifications.models import Notification

    # Find all non handled notifications related to this transfer
    notifications = Notification.objects(
        details__transfer_subject=transfer.subject,
        details__transfer_owner=transfer.owner,
        details__transfer_recipient=transfer.recipient,
        handled_at=None,
    )

    # Update handled_at for all matching notifications
    for notification in notifications:
        notification.handled_at = datetime.utcnow()
        notification.save()


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
