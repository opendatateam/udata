import logging

from datetime import datetime


from udata.auth import login_required, current_user
from udata.models import Organization, User

from .models import Transfer
from .permissions import TransferPermission, TransferResponsePermission

log = logging.getLogger(__name__)


@login_required
def request_transfer(subject, recipient, comment):
    '''Initiate a transfer request'''
    TransferPermission(subject).test()
    if recipient == (subject.organization or subject.owner):
        raise ValueError(
            'Recipient should be different than the current owner')
    transfer = Transfer.objects.create(
        owner=subject.organization or subject.owner,
        recipient=recipient,
        subject=subject,
        comment=comment
    )
    return transfer


@login_required
def accept_transfer(transfer, comment=None):
    '''Accept an incoming a transfer request'''
    TransferResponsePermission(transfer).test()

    transfer.responded = datetime.utcnow()
    transfer.responder = current_user._get_current_object()
    transfer.status = 'accepted'
    transfer.response_comment = comment
    transfer.save()

    subject = transfer.subject
    recipient = transfer.recipient
    if isinstance(recipient, Organization):
        subject.organization = recipient
    elif isinstance(recipient, User):
        subject.owner = recipient

    subject.save()

    return transfer


@login_required
def refuse_transfer(transfer, comment=None):
    '''Refuse an incoming a transfer request'''
    TransferResponsePermission(transfer).test()

    transfer.responded = datetime.utcnow()
    transfer.responder = current_user._get_current_object()
    transfer.status = 'refused'
    transfer.response_comment = comment
    transfer.save()

    return transfer
