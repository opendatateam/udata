"""
Delete the discussions that no subject can display: those opened on a model that
does not support discussions, and those without any subject at all.

`Discussion.subject` used to accept any registered document, and to be optional,
so a discussion could be opened on e.g. a `License`, or on nothing. Such a
discussion is displayed nowhere, notifies nobody, and crashes every listing of
the discussions since `self_web_url()` is only defined on the models of
`DISCUSSION_SUBJECTS`.

The field is now restricted to those classes and required; this removes the
documents written before that constraint existed.
"""

import logging
from collections import Counter
from datetime import UTC, datetime

from bson import DBRef

from udata.core.discussions.constants import DISCUSSION_SUBJECTS
from udata.search import unindex

log = logging.getLogger(__name__)


def migrate(db):
    # Raw queries and no mongoengine: dereferencing those subjects or emitting
    # the deletion signals is exactly what crashes on them.
    # `$nin` also matches the documents where the path is missing, which is how
    # the subject-less discussions are caught here.
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

    # Same for the notifications: `cleanup_discussion_notifications` deletes them
    # on `on_discussion_deleted`, and a notification pointing at a deleted
    # discussion makes the whole notification listing crash for its recipient.
    notifications = db.notification.delete_many({"details.discussion": {"$in": ids}})
    log.info(f"Deleted {notifications.deleted_count} notification(s)")

    deleted = db.discussion.delete_many({"_id": {"$in": ids}})
    log.info(f"Deleted {deleted.deleted_count} discussion(s) on an unsupported subject")

    # `unindex_model_on_delete` is connected to `post_delete`, which the raw
    # deletion above does not emit: without this the discussions would stay in
    # the search index for good. Unindexing only needs the id, so unlike the
    # deletion itself it can go through the regular task.
    for discussion_id in ids:
        unindex.delay("Discussion", str(discussion_id))
