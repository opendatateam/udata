"""
Index the activities on the kind of their actor, for the `actor_kind` filter.

It lists what harvesting or API tokens did. API tokens act far less often than
harvesting: without an index, finding their activities scans the collection by date.

Created here rather than in `Activity.meta`: mongoengine refuses to index a subfield of
a generic reference.

Mongoengine filters every query on `_cls`, listing all the activity kinds. `_cls` comes
last rather than as the prefix mongoengine gives the indexes it builds: placed before
the date, a page would merge one range per activity kind to come out sorted. Last, the
page reads a single sorted range per actor kind, and the count of the pagination is
answered from the index without fetching the activities.
"""

import logging

from pymongo import ASCENDING, DESCENDING

log = logging.getLogger(__name__)

INDEX_NAME = "actor_kind_created_at"


def migrate(db):
    log.info("Indexing the activities on the kind of their actor...")
    db.activity.create_index(
        [("actor._cls", ASCENDING), ("created_at", DESCENDING), ("_cls", ASCENDING)],
        name=INDEX_NAME,
    )
    log.info("Done")
