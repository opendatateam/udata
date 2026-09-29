import logging
from datetime import UTC, datetime

from udata.auth import current_user, login_required
from udata.models import Organization, User

from .models import Transfer
from .permissions import TransferPermission, TransferResponsePermission

log = logging.getLogger(__name__)


@login_required
def request_transfer(subject, recipient, comment):
    """Initiate a transfer request"""
    TransferPermission(subject).test()
    if recipient == (subject.organization or subject.owner):
        raise ValueError("Recipient should be different than the current owner")
    transfer = Transfer.objects.create(
        user=current_user._get_current_object(),
        owner=subject.organization or subject.owner,
        recipient=recipient,
        subject=subject,
        comment=comment,
    )
    return transfer


@login_required
def accept_transfer(transfer, comment=None):
    """Accept an incoming a transfer request"""
    TransferResponsePermission(transfer).test()

    subject = transfer.subject
    recipient = transfer.recipient

    # Contact points belong to an owner, so they cannot follow the subject as-is: each one
    # is replaced by its equivalent under the recipient. Reuses have no contact points at
    # all, hence the `getattr`. Resolved before the transfer is marked accepted because
    # `for_owner` writes to the database and can fail, and a transfer that has already
    # responded is refused by the API, leaving no way to retry.
    contact_points = [
        contact_point.for_owner(recipient)
        for contact_point in getattr(subject, "contact_points", None) or []
    ]

    transfer.responded = datetime.now(UTC)
    transfer.responder = current_user._get_current_object()
    transfer.status = "accepted"
    transfer.response_comment = comment
    transfer.save()
    Transfer.after_handle.send(transfer)

    if isinstance(recipient, Organization):
        subject.organization = recipient
    elif isinstance(recipient, User):
        subject.owner = recipient
    if contact_points:
        subject.contact_points = contact_points

    subject.save()

    return transfer


@login_required
def refuse_transfer(transfer, comment=None):
    """Refuse an incoming a transfer request"""
    TransferResponsePermission(transfer).test()

    transfer.responded = datetime.now(UTC)
    transfer.responder = current_user._get_current_object()
    transfer.status = "refused"
    transfer.response_comment = comment
    transfer.save()
    Transfer.after_handle.send(transfer)

    return transfer
