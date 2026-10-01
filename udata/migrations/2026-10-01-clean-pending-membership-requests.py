"""
Leave at most one pending membership request or invitation per user and organization, none for
members, and remove members listed twice.

A user could ask to join an organization they were already invited to, and an email invitation
stayed unlinked when the account's address differed in case or was changed afterwards: joining
through one entry left the others pending, and admins were shown requests that could only fail.

Email invitations matching an account are linked to it, as on registration. Then, for each user,
the first pending entry is kept and the others are removed, all of them for members. Nobody
handled the removed entries, so they are not marked as accepted or refused.
"""

import logging
from datetime import UTC, datetime

from udata.core.organization.notifications import MembershipRequestNotificationDetails
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

        kept_requests = []
        kept_kinds = {}
        # Only entries that had a user got notifications.
        deleted_notified = set()
        linked_invitations = []
        for req in requests:
            if req.get("status") != "pending":
                kept_requests.append(req)
                continue
            kind = req.get("kind", "request")
            user_id = req.get("user")
            had_user = user_id is not None
            if not had_user:
                user_id = user_ids_by_email.get((req.get("email") or "").lower())
            if user_id and (user_id in member_ids or user_id in kept_kinds):
                if had_user:
                    deleted_notified.add((user_id, kind))
                continue
            if user_id and not had_user:
                req = {**req, "user": user_id, "email": None}
                linked_invitations.append(req)
            if user_id:
                kept_kinds[user_id] = kind
            kept_requests.append(req)

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
        # Unlinked invitations had no user to notify: notify them now, as on registration. The
        # notification of a deleted invitation of the same user was kept above for this one.
        for req in linked_invitations:
            if Notification.objects(
                user=req["user"],
                details__request_organization=org["_id"],
                details__request_user=req["user"],
                handled_at=None,
            ).first():
                continue
            Notification(
                user=req["user"],
                created_at=req["created"],
                details=MembershipRequestNotificationDetails(
                    request_organization=org["_id"], request_user=req["user"], kind="invitation"
                ),
            ).save()

    log.info(f"Linked {linked_count} email invitations to their account")
    log.info(f"Deleted {deleted_count} redundant pending requests and invitations")
    log.info(f"Removed {duplicate_count} duplicated members")
