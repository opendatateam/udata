"""
Remove pending membership requests and invitations left behind by deleted user accounts.

`User.mark_as_deleted` only recently started removing an account's pending organization
membership requests (ref datagouv/data.gouv.fr#2108). Accounts deleted before that fix kept
theirs, and nothing else ever purged them, so organization admins kept seeing requests from
accounts that no longer exist.

Pending entries whose `user` is a deleted account are dropped. Handled history
(accepted/refused/canceled entries) and email-only invitations, which have no user, are kept.
The removed entries are dropped rather than marked as refused: they were abandoned, not
decided. The notifications about the removed entries are deleted, as `mark_as_deleted`
already does for the accounts it processes.
"""

import logging

from udata.core.organization.models import Organization
from udata.core.user.models import User
from udata.features.notifications.models import Notification

log = logging.getLogger(__name__)


def migrate(db):
    deleted_ids = User._get_collection().distinct("_id", {"deleted": {"$ne": None}})
    if not deleted_ids:
        log.info("No deleted account, nothing to do")
        return

    # A `$pull` targets the matching entries without rewriting the whole `requests` array.
    pending_of_deleted = {"user": {"$in": deleted_ids}, "status": "pending"}
    result = Organization._get_collection().update_many(
        {"requests": {"$elemMatch": pending_of_deleted}},
        {"$pull": {"requests": pending_of_deleted}},
    )
    Notification.objects(details__request_user__in=deleted_ids).delete()

    log.info(f"Removed pending requests and invitations from {result.modified_count} organizations")
