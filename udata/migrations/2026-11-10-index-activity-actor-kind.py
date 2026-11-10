"""
Index the activities on the kind of their actor, for the `actor_kind` filter.

It lists what harvesting or API tokens did. API tokens act far less often than
harvesting: without an index, finding their activities scans the collection by date.

Created here rather than in `Activity.meta`: mongoengine refuses to index a subfield of
a generic reference. Left without the `_cls` prefix mongoengine gives the indexes it
builds, so a query merges one range per actor kind rather than one per activity kind.
"""

import logging

from pymongo import ASCENDING, DESCENDING

log = logging.getLogger(__name__)

INDEX_NAME = "actor_kind_created_at"


def migrate(db):
    log.info("Indexing the activities on the kind of their actor...")
    db.activity.create_index(
        [("actor._cls", ASCENDING), ("created_at", DESCENDING)], name=INDEX_NAME
    )
    log.info("Done")
