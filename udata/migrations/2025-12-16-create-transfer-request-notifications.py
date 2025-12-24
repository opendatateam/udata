"""
Create TransferRequestNotification for all pending transfer requests
"""

import logging

import click

from udata.core.organization.models import Organization
from udata.core.user.models import User
from udata.features.notifications.models import Notification
from udata.features.transfer.models import Transfer
from udata.features.transfer.notifications import TransferRequestNotificationDetails

log = logging.getLogger(__name__)


def migrate(db):
    log.info("Processing pending transfer requests...")

    created_count = 0

    # Get all pending transfers
    transfers = Transfer.objects(status="pending")

    with click.progressbar(transfers, length=transfers.count()) as transfer_list:
        for transfer in transfer_list:
            # Get the recipient (could be a user or an organization)
            recipient = transfer.recipient

            # For organizations, we need to find admins who should receive notifications
            if recipient._cls == "Organization":
                # Get all admin users for this organization
                recipient_users = [
                    member.user for member in recipient.members if member.role == "admin"
                ]
            else:
                # For users, just use the recipient directly
                recipient_users = [recipient]

            # Create a notification for each recipient user
            for recipient_user in recipient_users:
                try:
                    # Check if notification already exists
                    existing = Notification.objects(
                        user=recipient_user,
                        details__transfer_recipient=recipient,
                        details__transfer_owner=transfer.owner,
                        details__transfer_subject=transfer.subject,
                    ).first()
                    if not existing:
                        notification = Notification(user=recipient_user)
                        notification.details = TransferRequestNotificationDetails(
                            transfer_owner=transfer.owner,
                            transfer_recipient=recipient,
                            transfer_subject=transfer.subject,
                        )
                        # Set the created_at to match the transfer creation date
                        notification.created_at = transfer.created
                        notification.save()
                        created_count += 1
                except Exception as e:
                    log.error(
                        f"Error creating notification for user {recipient_user.id} "
                        f"and transfer {transfer.id}: {e}"
                    )
                    continue

    log.info(f"Created {created_count} TransferRequestNotifications")
