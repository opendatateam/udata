"""
Rename the `admin` scope of API tokens to `sysadmin`.

Every token got `admin` by default. A sysadmin's token keeps the sysadmin rights it had,
under the new name. Anyone else's loses a scope they never chose and which granted them
nothing: kept, it would hand the sysadmin rights to their tokens on a promotion.
"""

import logging

from mongoengine.connection import get_db

log = logging.getLogger(__name__)


def migrate(db):
    db = get_db()
    admin_role = db.role.find_one({"name": "admin"}, {"_id": 1})
    sysadmin_ids = db.user.distinct("_id", {"roles": admin_role["_id"]}) if admin_role else []

    renamed = db.api_token.update_many(
        {"scopes": "admin", "user": {"$in": sysadmin_ids}},
        {"$set": {"scopes": ["sysadmin"]}},
    )
    log.info(f"{renamed.modified_count} sysadmin tokens now hold the `sysadmin` scope.")

    dropped = db.api_token.update_many({"scopes": "admin"}, {"$set": {"scopes": []}})
    log.info(f"{dropped.modified_count} tokens of other users lost the `admin` scope.")
