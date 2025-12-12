"""
Migrate SpamInfo embedded documents to Report objects.

The old spam detection system stored spam status in a SpamInfo embedded document
on Discussion models. This migration converts those to Report objects with
reason="auto_spam".

Old structure (on Discussion):
    spam = {
        "status": "potential_spam" | "no_spam" | "not_checked",
        "callbacks": {"method_name": {"args": [...], "kwargs": {...}}}
    }

New structure (Report document):
    subject = DBRef to Discussion
    reason = "auto_spam"
    callbacks = {"method_name": {"args": [...], "kwargs": {...}}}
    dismissed_at = set for no_spam (false positives that were reviewed)
"""

import logging
from datetime import datetime

from bson import DBRef

log = logging.getLogger(__name__)

POTENTIAL_SPAM = "potential_spam"
NO_SPAM = "no_spam"
REASON_AUTO_SPAM = "auto_spam"


def migrate(db):
    log.info("Migrating SpamInfo to Reports...")

    discussion_collection = db.discussion
    report_collection = db.report

    # Find all discussions with potential_spam or no_spam status
    query = {"spam.status": {"$in": [POTENTIAL_SPAM, NO_SPAM]}}
    discussions_docs = list(discussion_collection.find(query))

    created_count = 0
    dismissed_count = 0
    skipped_count = 0

    for doc in discussions_docs:
        discussion_id = doc["_id"]
        spam_info = doc.get("spam", {})
        status = spam_info.get("status")
        callbacks = spam_info.get("callbacks", {})

        # Check if a Report already exists for this discussion
        subject_ref = DBRef("discussion", discussion_id)
        existing = report_collection.find_one({"subject": subject_ref, "reason": REASON_AUTO_SPAM})
        if existing:
            log.debug(f"Report already exists for discussion {discussion_id}, skipping")
            skipped_count += 1
            continue

        # Create the Report document
        report_doc = {
            "subject": subject_ref,
            "reason": REASON_AUTO_SPAM,
            "message": "Migrated from legacy SpamInfo",
            "reported_at": datetime.utcnow(),
        }

        if status == NO_SPAM:
            # no_spam means it was reviewed and dismissed (false positive)
            report_doc["dismissed_at"] = datetime.utcnow()
            # Callbacks were already executed, no need to store them
            dismissed_count += 1
        else:
            # potential_spam - still pending review
            report_doc["callbacks"] = callbacks
            created_count += 1

        report_collection.insert_one(report_doc)
        log.debug(f"Created Report for discussion {discussion_id} (status={status})")

    log.info(
        f"Migration complete: {created_count} pending Reports, "
        f"{dismissed_count} dismissed Reports, {skipped_count} skipped"
    )

    # Clean up the spam field from all discussions (including not_checked)
    result = discussion_collection.update_many(
        {"spam": {"$exists": True}}, {"$unset": {"spam": ""}}
    )
    log.info(f"Cleaned up spam field from {result.modified_count} discussions")
