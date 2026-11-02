"""
Delete pending transfers requested by a former owner of their subject, and their notifications.

A pending transfer outlived a change of owner of its subject: accepting it took the subject
from its new owner. Transfers are now dropped when the owner changes, this removes those
left over from before.
"""

import logging

from udata.features.transfer.models import Transfer

log = logging.getLogger(__name__)


def migrate(db):
    stale_ids = [
        transfer.id
        for transfer in Transfer.objects(status="pending")
        if transfer.owner != (transfer.subject.organization or transfer.subject.owner)
    ]
    # Deleted through the model so that the receiver of `post_delete` drops the notifications.
    Transfer.objects(id__in=stale_ids).delete()
    log.info(f"Deleted {len(stale_ids)} stale pending transfers")
