"""
Delete pending membership requests and invitations of users who are already members,
and remove members listed twice.

Adding a member used to leave their pending requests and invitations untouched: admins were
shown requests that could only fail with a 409. Nobody accepted those requests, so marking them
as accepted would invent a decision; they are removed instead.
"""

import logging
from datetime import UTC, datetime

from udata.features.notifications.models import Notification

log = logging.getLogger(__name__)


def migrate(db):
    now = datetime.now(UTC)
    deleted_count = 0
    duplicate_count = 0

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

        member_emails = set()
        if any(r.get("status") == "pending" and r.get("email") for r in requests):
            member_emails = {
                u["email"].lower()
                for u in db.user.find({"_id": {"$in": list(member_ids)}}, {"email": 1})
                if u.get("email")
            }

        kept_requests = []
        deleted_user_ids = set()
        for req in requests:
            email = req.get("email")
            is_member = (req.get("user") and req["user"] in member_ids) or (
                email and email.lower() in member_emails
            )
            if req.get("status") == "pending" and is_member:
                if req.get("user"):
                    deleted_user_ids.add(req["user"])
                continue
            kept_requests.append(req)

        deleted = len(requests) - len(kept_requests)
        removed = len(members) - len(unique_members)
        if not deleted and not removed:
            continue

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
        if deleted_user_ids:
            Notification.objects(
                details__request_organization=org["_id"],
                details__request_user__in=list(deleted_user_ids),
                handled_at=None,
            ).update(set__handled_at=now)

    log.info(f"Deleted {deleted_count} pending requests and invitations of members")
    log.info(f"Removed {duplicate_count} duplicated members")
