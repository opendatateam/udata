"""
Fix Report subject field format.

The 2025-11-27 SpamInfo migration stored `subject` as a raw DBRef
(e.g. DBRef("discussion", ObjectId("..."))) instead of the
GenericLazyReferenceField format {"_cls": "Discussion", "_ref": DBRef(...)}.

This causes crashes in select_related/dereference because
GenericLazyReferenceField has no `document_type` attribute.
"""

import logging

from bson import DBRef

log = logging.getLogger(__name__)

COLLECTION_TO_CLASS = {
    "dataset": "Dataset",
    "reuse": "Reuse",
    "discussion": "Discussion",
    "organization": "Organization",
    "dataservice": "Dataservice",
}


def migrate(db):
    log.info("Fixing Report subject DBRef format...")

    report_collection = db.report
    fixed_count = 0

    for report in report_collection.find(
        {"subject._cls": {"$exists": False}, "subject.$ref": {"$exists": True}}
    ):
        subject = report["subject"]
        if not isinstance(subject, DBRef):
            continue

        cls_name = COLLECTION_TO_CLASS.get(subject.collection)
        if not cls_name:
            log.warning(
                f"Unknown collection '{subject.collection}' for report {report['_id']}, skipping"
            )
            continue

        report_collection.update_one(
            {"_id": report["_id"]},
            {"$set": {"subject": {"_cls": cls_name, "_ref": subject}}},
        )
        fixed_count += 1

    log.info(f"Fixed {fixed_count} reports with raw DBRef subjects")
