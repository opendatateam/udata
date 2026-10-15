"""
Remove pending membership requests and invitations left behind by deleted user accounts.

`User.mark_as_deleted` only recently started removing an account's pending organization
membership requests (ref datagouv/data.gouv.fr#2108). Accounts deleted before that fix kept
theirs, and nothing else ever purged them, so organization admins kept seeing requests from
accounts that no longer exist.

Pending entries whose `user` is a deleted account — or a hard-deleted one, whose document is
gone entirely — are dropped. Handled history (accepted/refused/canceled entries) and email-only
invitations, which have no user, are kept. As for redundant entries, the removed ones are dropped
rather than marked as refused: they were abandoned, not decided. The pending admin notifications
for the removed entries are marked handled, like in the migration cleaning redundant pending
requests.
"""

import logging
from datetime import UTC, datetime

from udata.core.organization.models import Organization
from udata.core.user.models import User
from udata.features.notifications.constants import NotificationType
from udata.features.notifications.models import Notification

log = logging.getLogger(__name__)

NOTIFICATION_TYPES = {
    "request": NotificationType.ORGANIZATION_MEMBERSHIP_REQUESTED,
    "invitation": NotificationType.ORGANIZATION_MEMBERSHIP_INVITED,
}


def migrate(db):
    now = datetime.now(UTC)
    deleted_count = 0

    organizations = Organization._get_collection()
    users = User._get_collection()

    candidate_ids = organizations.distinct(
        "requests.user",
        {"requests": {"$elemMatch": {"status": "pending", "user": {"$ne": None}}}},
    )
    if not candidate_ids:
        log.info("No pending membership requests with a user, nothing to do")
        return

    # Deleted accounts keep their document with `deleted` set; hard-deleted accounts have no
    # document left at all. Both leave unresolvable references in pending requests.
    existing_ids = set(users.distinct("_id", {"_id": {"$in": candidate_ids}}))
    deleted_ids = set(
        users.distinct("_id", {"_id": {"$in": candidate_ids}, "deleted": {"$ne": None}})
    )
    gone_ids = (set(candidate_ids) - existing_ids) | deleted_ids
    if not gone_ids:
        log.info("No pending membership requests from deleted users, nothing to do")
        return

    # Raw documents: going through the model would dereference every request user, and fail on
    # accounts whose document no longer exists.
    for org in organizations.find({"requests.user": {"$in": list(gone_ids)}}, {"requests": 1}):
        requests = org.get("requests") or []
        removed_pairs = set()
        kept_requests = []
        for req in requests:
            if req.get("user") in gone_ids and req.get("status") == "pending":
                removed_pairs.add((req.get("user"), req.get("kind") or "request"))
                continue
            kept_requests.append(req)

        if len(kept_requests) == len(requests):
            continue

        deleted_count += len(requests) - len(kept_requests)
        organizations.update_one({"_id": org["_id"]}, {"$set": {"requests": kept_requests}})
        for user_id, kind in removed_pairs:
            Notification.objects(
                type=NOTIFICATION_TYPES[kind],
                details__request_organization=org["_id"],
                details__request_user=user_id,
                handled_at=None,
            ).mark_handled(at=now)

    log.info(f"Deleted {deleted_count} pending requests and invitations from deleted accounts")
