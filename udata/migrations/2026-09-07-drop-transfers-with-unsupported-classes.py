"""
Until `Transfer` got `choices` on its generic references, the transfer API resolved the
`class` sent in the request body against the whole document registry. Transfers pointing
at a class a transfer means nothing for could therefore be created, and they are not just
dead rows: the listing endpoint marshals its whole result set with a `Polymorph` field,
which raises on the first unknown class — so a single one of them makes every transfer of
its recipient unreadable.

They cannot be repaired (there is no sensible class to move them to) and none of them can
ever be accepted, so they are removed.
"""

import logging

from udata.features.transfer.models import TRANSFER_PERSONS, TRANSFERABLE_SUBJECTS, Transfer

log = logging.getLogger(__name__)


def migrate(db):
    log.info("Dropping transfers whose subject, recipient or owner is not transferable")

    unsupported = Transfer.objects(
        __raw__={
            "$or": [
                {"subject._cls": {"$nin": TRANSFERABLE_SUBJECTS}},
                {"recipient._cls": {"$nin": TRANSFER_PERSONS}},
                {"owner._cls": {"$nin": TRANSFER_PERSONS}},
            ]
        }
    )

    for transfer in unsupported.no_dereference():
        # `to_mongo` rather than the attributes: the referenced document may itself be
        # gone, and dereferencing it would raise instead of logging what we are removing.
        raw = transfer.to_mongo()
        log.info(
            "Dropping transfer %s (subject=%s, recipient=%s, owner=%s, status=%s)",
            transfer.id,
            raw.get("subject", {}).get("_cls"),
            raw.get("recipient", {}).get("_cls"),
            raw.get("owner", {}).get("_cls"),
            raw.get("status"),
        )

    log.info("Dropped %s transfer(s)", unsupported.delete())
