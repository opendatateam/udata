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
    stale = [
        transfer
        for transfer in Transfer.objects(status="pending")
        if transfer.owner != (transfer.subject.organization or transfer.subject.owner)
    ]
    for transfer in stale:
        transfer.delete()
    log.info(f"Deleted {len(stale)} stale pending transfers")
