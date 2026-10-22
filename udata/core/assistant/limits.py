from datetime import datetime, timezone

from flask import current_app

from udata.app import cache

QUOTA_KEY_PREFIX = "assistant-quota"
# Daily counter: 24 hours is enough for the reset to happen on the next day.
QUOTA_TTL = 24 * 60 * 60


class QuotaExceeded(RuntimeError):
    """Raised when a user has exhausted their daily assistant quota."""


def check_and_consume_quota(user_id: str) -> None:
    """Increment the daily call counter for a user and enforce the quota.

    Raises QuotaExceeded once the user has consumed ASSISTANT_QUOTA_PER_USER
    calls for the current day.
    """
    quota = current_app.config["ASSISTANT_QUOTA_PER_USER"]
    today = datetime.now(timezone.utc).date().isoformat()
    key = f"{QUOTA_KEY_PREFIX}:{user_id}:{today}"
    count = (cache.get(key) or 0) + 1
    cache.set(key, count, timeout=QUOTA_TTL)
    if count > quota:
        raise QuotaExceeded(f"Assistant quota exceeded for user {user_id} on {today}")
