"""
Leave at most one pending membership request or invitation per user and organization, none for
members, and remove members listed twice.

Members could be added directly by an admin (the endpoint removed in #3570), which left their
pending requests behind; a user could also ask to join an organization they were already invited
to, and an email invitation stayed unlinked when the account's address differed in case or was
changed afterwards. Admins were shown entries that could only fail.

Email invitations matching an account are linked to it, as on registration. Then, for each user,
a single pending entry is kept and the others are removed, all of them for members. As in
`match_email_invitations`, an entry already linked to the account wins over an email invitation,
otherwise the first one in the array is kept. The removed entries are dropped rather than marked
as accepted or refused: they were superseded, not decided.
"""

import logging
from datetime import UTC, datetime

from udata.core.organization.models import MembershipRequest
from udata.core.organization.notifications import _create_membership_notification
from udata.features.notifications.models import Notification

log = logging.getLogger(__name__)


def migrate(db):
    now = datetime.now(UTC)
    linked_count = 0
    deleted_count = 0
    duplicate_count = 0

    pending_emails = db.organization.distinct(
        "requests.email", {"requests": {"$elemMatch": {"status": "pending", "kind": "invitation"}}}
    )
    # Accounts keep the case of their email as typed at registration.
    user_ids_by_email = {
        u["email"].lower(): u["_id"]
        for u in db.user.find(
            {"email": {"$in": [e for e in pending_emails if e]}},
            {"email": 1},
            collation={"locale": "en", "strength": 2},
        )
    }

    # Raw documents: going through the model would dereference every member, and fail on
    # members whose account no longer exists.
    for org in db.organization.find({}, {"members": 1, "requests": 1}):
        members = org.get("members") or []
        requests = org.get("requests") or []

        member_ids = set()
        unique_members = []
        for member in members:
            if member.get("user") in member_ids:
                continue
            member_ids.add(member.get("user"))
            # The first entry is the one the application reads (`Organization.member`).
            unique_members.append(member)

        kept_kinds = {}
        # Only entries that had a user got notifications.
        deleted_notified = set()
        deleted_indexes = set()
        linked_by_index = {}
        pending = [(i, req) for i, req in enumerate(requests) if req.get("status") == "pending"]
        # Entries already linked to an account win over email invitations, as in
        # `match_email_invitations` (stable sort: the array order decides among each group).
        pending.sort(key=lambda item: item[1].get("user") is None)
        for i, req in pending:
            kind = req.get("kind", "request")
            user_id = req.get("user")
            had_user = user_id is not None
            if not had_user:
                user_id = user_ids_by_email.get((req.get("email") or "").lower())
            if user_id and (user_id in member_ids or user_id in kept_kinds):
                if had_user:
                    deleted_notified.add((user_id, kind))
                deleted_indexes.add(i)
                continue
            if user_id and not had_user:
                linked_by_index[i] = {**req, "user": user_id, "email": None}
            if user_id:
                kept_kinds[user_id] = kind
        kept_requests = [
            linked_by_index.get(i, req)
            for i, req in enumerate(requests)
            if i not in deleted_indexes
        ]
        linked_invitations = list(linked_by_index.values())

        deleted = len(requests) - len(kept_requests)
        removed = len(members) - len(unique_members)
        if not deleted and not removed and not linked_invitations:
            continue

        linked_count += len(linked_invitations)
        deleted_count += deleted
        duplicate_count += removed
        db.organization.update_one(
            {"_id": org["_id"]},
            {
                "$set": {
                    "members": unique_members,
                    "requests": kept_requests,
                    "metrics.members": len(unique_members),
                }
            },
        )
        # Notifications are keyed by user and kind: keep the one of the entry left pending.
        # Request notifications created before invitations existed have no `kind`.
        for user_id, kind in deleted_notified:
            if kept_kinds.get(user_id) == kind:
                continue
            Notification.objects(
                details__request_organization=org["_id"],
                details__request_user=user_id,
                details__kind__in=[kind, None] if kind == "request" else [kind],
                handled_at=None,
            ).update(set__handled_at=now)
        # Unlinked invitations had no user to notify: notify them now, as on registration.
        for req in linked_invitations:
            _create_membership_notification(
                MembershipRequest(user=req["user"], kind="invitation", created=req["created"]),
                org["_id"],
                req["user"],
            )

    log.info(f"Linked {linked_count} email invitations to their account")
    log.info(f"Deleted {deleted_count} redundant pending requests and invitations")
    log.info(f"Removed {duplicate_count} duplicated members")
