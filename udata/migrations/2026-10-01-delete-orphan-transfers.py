"""
Delete transfers, and transfer notifications, referencing a document that no longer exists.

Deleting a topic left its transfers behind, and the purges of transferred objects left the
notifications of their transfers behind. Dereferencing them raises: a single one made every
transfer, or every notification, of its recipient unreadable.
"""

import logging

log = logging.getLogger(__name__)

TRANSFER_FIELDS = ("subject", "owner", "recipient")


def migrate(db):
    known = {}

    def exists(reference):
        # Raw documents: the model would dereference the very references being checked.
        ref = reference["_ref"]
        key = (ref.collection, ref.id)
        if key not in known:
            known[key] = db[ref.collection].count_documents({"_id": ref.id}, limit=1) > 0
        return known[key]

    def is_orphan(document, fields):
        return any(document.get(f) and not exists(document[f]) for f in fields)

    transfer_ids = [
        t["_id"]
        for t in db.transfer.find({}, {f: 1 for f in TRANSFER_FIELDS})
        if is_orphan(t, TRANSFER_FIELDS)
    ]
    db.transfer.delete_many({"_id": {"$in": transfer_ids}})
    log.info(f"Deleted {len(transfer_ids)} orphan transfers")

    notification_fields = tuple(f"transfer_{f}" for f in TRANSFER_FIELDS)
    notification_ids = [
        n["_id"]
        for n in db.notification.find(
            {"details._cls": "TransferRequestNotificationDetails"}, {"details": 1}
        )
        if is_orphan(n["details"], notification_fields)
    ]
    db.notification.delete_many({"_id": {"$in": notification_ids}})
    log.info(f"Deleted {len(notification_ids)} orphan transfer notifications")
