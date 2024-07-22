"""
Remove Transfer db integrity problems
⚠️ long migration
"""

import logging

import mongoengine

from udata.models import Transfer

log = logging.getLogger(__name__)


def migrate(db):
    log.info("Processing Transfer objects.")

    transfers = Transfer.objects.no_cache().all()

    count = 0
    for transfer in transfers:
        try:
            transfer.subject.id
            transfer.owner.id
            transfer.recipient.id
        except mongoengine.errors.DoesNotExist:
            transfer.delete()
            count += 1

    log.info(f"Completed, removed {count} Transfer objects")
