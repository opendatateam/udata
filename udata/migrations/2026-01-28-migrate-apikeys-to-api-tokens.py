"""
Migrate existing User.apikey values to the new ApiToken collection.
Each existing apikey is hashed with HMAC-SHA256 (keyed on API_TOKEN_SECRET)
and stored in the new api_token collection.
The old apikey field is then removed from all user documents.
"""

import hashlib
import hmac
import logging
from datetime import datetime, timezone

from flask import current_app

log = logging.getLogger(__name__)


def migrate(db):
    log.info("Migrating user API keys to new api_token collection...")

    users = db.user.find({"apikey": {"$ne": None, "$exists": True}})
    api_token_collection = db.api_token

    migrated = 0
    skipped = 0

    for user in users:
        apikey = user["apikey"]
        if not apikey:
            continue

        key = current_app.config["API_TOKEN_SECRET"].encode()
        token_hash = hmac.new(key, apikey.encode(), hashlib.sha256).hexdigest()

        if api_token_collection.find_one({"token_hash": token_hash}):
            skipped += 1
            continue

        prefix = apikey[:8] if len(apikey) >= 8 else apikey

        api_token_collection.insert_one(
            {
                "token_hash": token_hash,
                "token_prefix": prefix,
                "user": user["_id"],
                "name": "Migrated API key",
                "scope": "admin",
                "kind": "api_key",
                "created_at": datetime.now(timezone.utc),
                "last_used_at": None,
                "user_agents": [],
                "revoked_at": None,
                "expires_at": None,
            }
        )
        migrated += 1

    db.user.update_many({}, {"$unset": {"apikey": ""}})

    log.info(f"Migration complete. {migrated} keys migrated, {skipped} skipped (already existed).")
