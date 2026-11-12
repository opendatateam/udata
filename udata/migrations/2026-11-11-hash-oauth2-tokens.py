"""
Replace the OAuth2 client secrets, access tokens and refresh tokens stored in clear by their
hashes.

The clients keep the plaintexts they already hold: the lookups now hash what they receive.
"""

import logging
import re

from pymongo import UpdateOne

from udata.core.api_token.models import hash_token

log = logging.getLogger(__name__)

BATCH_SIZE = 1000

# A `hash_token` hexdigest. Authlib's tokens (42 and 48 characters) and the secrets made by
# `create_oauth_client` (50) never match it, so the migration can be run again: after a failed
# run, or through `udata db unrecord` to catch up the tokens written in clear by a worker still
# on the previous code.
HASH = re.compile(r"[0-9a-f]{64}")


def hash_in_clear_values(collection, fields):
    updates = []
    count = 0
    for document in collection.find({}, {field: 1 for field in fields}):
        hashed = {
            field: hash_token(document[field])
            for field in fields
            if document.get(field) and not HASH.fullmatch(document[field])
        }
        if hashed:
            updates.append(UpdateOne({"_id": document["_id"]}, {"$set": hashed}))
        if len(updates) == BATCH_SIZE:
            collection.bulk_write(updates)
            count += len(updates)
            updates = []
    if updates:
        collection.bulk_write(updates)
        count += len(updates)
    log.info(f"Hashed the values of {count} documents in {collection.name}")


def migrate(db):
    hash_in_clear_values(db.oauth2_client, ["secret"])
    hash_in_clear_values(db.oauth2_token, ["access_token", "refresh_token"])
