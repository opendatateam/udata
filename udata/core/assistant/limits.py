import logging
from datetime import datetime, timezone

from flask import current_app
from flask_caching.backends import NullCache

from udata.app import cache

log = logging.getLogger(__name__)

QUOTA_KEY_PREFIX = "assistant-quota"
# Daily counter: 24 hours is enough for the reset to happen on the next day.
QUOTA_TTL = 24 * 60 * 60

# Deliberate fail-open: when the cache backend is a NullCache (no-op, as in the
# default dev/test config), the quota counter silently does nothing and the
# assistant stays available. Availability of the assistant beats quota
# strictness when the cache is non-functional; the warning below makes the
# choice visible instead of silent. This must not become fail-closed without a
# product decision.
_null_cache_warned = False


class QuotaExceeded(RuntimeError):
    """Raised when a user has exhausted their daily assistant quota."""


def check_and_consume_quota(user_id: str) -> None:
    """Increment the daily call counter for a user and enforce the quota.

    Raises QuotaExceeded once the user has consumed ASSISTANT_QUOTA_PER_USER
    calls for the current day. The quota is approximate: per-process counting
    (no shared store) and fail-open if the cache backend does not persist
    (e.g. NullCache), per spec V1.
    """
    global _null_cache_warned
    if not _null_cache_warned and isinstance(cache.cache, NullCache):
        _null_cache_warned = True
        log.warning(
            "Assistant quota is not enforced: the cache backend is a NullCache "
            "(no-op). This is a deliberate fail-open choice; configure a real "
            "CACHE_TYPE to enforce ASSISTANT_QUOTA_PER_USER."
        )
    quota = current_app.config["ASSISTANT_QUOTA_PER_USER"]
    today = datetime.now(timezone.utc).date().isoformat()
    key = f"{QUOTA_KEY_PREFIX}:{user_id}:{today}"
    count = (cache.get(key) or 0) + 1
    cache.set(key, count, timeout=QUOTA_TTL)
    if count > quota:
        raise QuotaExceeded(f"Assistant quota exceeded for user {user_id} on {today}")
