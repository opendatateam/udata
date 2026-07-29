"""
Delete the discussions opened on a model that does not support discussions.

`Discussion.subject` used to accept any registered document, so a discussion
could be opened on e.g. a `License`. Such a discussion is displayed nowhere,
notifies nobody, and crashes every listing of the discussions since
`self_web_url()` is only defined on the models of `DISCUSSION_SUBJECTS`.

The field now restricts the accepted classes; this removes the documents
written before that constraint existed.
"""

import logging
from collections import Counter
from datetime import UTC, datetime

from bson import DBRef

from udata.core.discussions.constants import DISCUSSION_SUBJECTS

log = logging.getLogger(__name__)


def migrate(db):
    # Raw queries and no mongoengine: dereferencing those subjects or emitting
    # the deletion signals is exactly what crashes on them.
    query = {"subject._cls": {"$nin": list(DISCUSSION_SUBJECTS)}}

    counts = Counter()
    ids = []
    for discussion in db.discussion.find(query, {"subject._cls": 1}):
        subject = discussion.get("subject")
        counts[subject.get("_cls") if isinstance(subject, dict) else None] += 1
        ids.append(discussion["_id"])

    if not ids:
        log.info("No discussion on an unsupported subject")
        return

    for subject_class, count in counts.most_common():
        log.info(f"\t{count} discussion(s) on {subject_class or 'no subject'}")

    # Pending reports on those discussions would otherwise stay in the
    # moderation queue, pointing at a deleted discussion.
    reports = db.report.update_many(
        {
            "subject._ref": {"$in": [DBRef("discussion", id) for id in ids]},
            "subject_deleted_at": None,
        },
        {"$set": {"subject_deleted_at": datetime.now(UTC)}},
    )
    log.info(f"Marked {reports.modified_count} report(s) as handled")

    deleted = db.discussion.delete_many({"_id": {"$in": ids}})
    log.info(f"Deleted {deleted.deleted_count} discussion(s) on an unsupported subject")
