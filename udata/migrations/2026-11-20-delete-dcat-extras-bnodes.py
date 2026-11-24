"""
Remove meaningless BNode identifiers from selected str/list[str] fields.
"""

import logging

from mongoengine.connection import get_db

log = logging.getLogger(__name__)


# resource fields that could contain BNode IDs
RESOURCE_FIELDS = ["format", "mime"]

# extra fields that could contain BNode IDs
EXTRAS_DCAT_FIELDS = ["license", "accessRights", "rights", "provenance", "spatial_resolution"]

# rdflib default BNode identifier pattern: f"N{uuid4().hex}" (lowercased by udata on some fields)
RX = {"$regex": r"^[Nn][0-9a-f]{32}$"}

# RX will match arrays of regex unless restricted
RX_UNIT = {**RX, "$not": {"$type": "array"}}


def migrate(db):
    log.info("Processing dataset collection...")
    db = get_db()

    for field in RESOURCE_FIELDS:
        # str field
        r = db.dataset.update_many(
            {f"resources.{field}": RX_UNIT},
            {"$unset": {f"resources.$[r].{field}": ""}},
            array_filters=[{f"r.{field}": RX_UNIT}],
        )
        # str array field
        # nothing to process in Resource
        log.info(f"- {field} (resource): {r.modified_count}")

    for field in EXTRAS_DCAT_FIELDS:
        path = f"extras.dcat.{field}"

        # Dataset extras
        # str field
        rs = db.dataset.update_many({path: RX_UNIT}, {"$unset": {path: ""}})
        # str array field
        ra = db.dataset.update_many({path: {"$elemMatch": RX}}, {"$pull": {path: RX}})
        db.dataset.update_many({path: {"$size": 0}}, {"$unset": {path: ""}})
        log.info(f"- {path} (dataset): {rs.modified_count + ra.modified_count}")

        # Resources extras
        rpath = f"resources.$[r].{path}"
        rid = f"r.{path}"
        # str field
        rrs = db.dataset.update_many(
            {"resources": {"$elemMatch": {path: RX_UNIT}}},
            {"$unset": {rpath: ""}},
            array_filters=[{rid: RX_UNIT}],
        )
        # str array field
        rra = db.dataset.update_many(
            {"resources": {"$elemMatch": {path: {"$elemMatch": RX}}}},
            {"$pull": {rpath: RX}},
            array_filters=[{rid: {"$elemMatch": RX}}],
        )
        db.dataset.update_many(
            {"resources": {"$elemMatch": {path: {"$size": 0}}}},
            {"$unset": {rpath: ""}},
            array_filters=[{rid: {"$size": 0}}],
        )
        log.info(f"- {path} (resource): {rrs.modified_count + rra.modified_count}")
