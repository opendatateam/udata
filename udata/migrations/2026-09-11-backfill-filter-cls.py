"""
This migration sets `_cls` to "Filter" on the elements of chart filter groups
(AndFilters/OrFilters `filters` lists) stored without one.

Those lists used to be plain `EmbeddedDocumentListField(Filter)` and so were
stored without a `_cls` key. Now that they are generic (they can hold Filter
or the other group class), elements missing `_cls` cannot be told apart from
groups on read and are never rewritten until the document is saved.
"""

import logging

from udata.core.visualizations.models import Chart

log = logging.getLogger(__name__)


def migrate(db):
    collection = Chart._get_collection()
    query = {"series.filters.filters": {"$elemMatch": {"_cls": {"$exists": False}}}}
    fixed = 0
    for raw in collection.find(query):
        changed = False
        for series in raw.get("series", []):
            group = series.get("filters") or {}
            for element in group.get("filters") or []:
                if isinstance(element, dict) and "_cls" not in element:
                    # Groups did not exist when those elements were written:
                    # they can only be plain filters.
                    element["_cls"] = "Filter"
                    changed = True
                    fixed += 1
        if changed:
            collection.replace_one({"_id": raw["_id"]}, raw)
    log.info(f"\tSet _cls='Filter' on {fixed} filter element(s)")
