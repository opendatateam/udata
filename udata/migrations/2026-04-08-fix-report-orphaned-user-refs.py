"""
Nullify orphaned user references in reports.

Some reports reference users that no longer exist in the database.
The `reverse_delete_rule=NULLIFY` on ReferenceField should handle this
automatically, but users deleted before that rule was in place (or via
raw MongoDB operations) left dangling DBRefs that crash the API during
marshalling.
"""

import logging

log = logging.getLogger(__name__)

USER_REF_FIELDS = ["by", "dismissed_by", "subject_deleted_by"]


def migrate(db):
    log.info("Fixing orphaned user references in reports...")

    report_collection = db.report
    user_collection = db.user

    existing_user_ids = set(doc["_id"] for doc in user_collection.find({}, {"_id": 1}))

    fixed_count = 0

    for report in report_collection.find():
        nullify = {}
        for field_name in USER_REF_FIELDS:
            ref = report.get(field_name)
            if ref is not None and ref.id not in existing_user_ids:
                nullify[field_name] = None

        if nullify:
            report_collection.update_one({"_id": report["_id"]}, {"$set": nullify})
            fixed_count += 1

    log.info(f"Fixed {fixed_count} reports with orphaned user references")
