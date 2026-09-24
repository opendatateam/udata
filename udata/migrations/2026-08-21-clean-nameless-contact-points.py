"""
Harvesting used to name a contact point after its `foaf:Agent` or `vcard:Kind`, falling back to
an empty string when neither carried a name, and to read an address out of a bare `mailto:`,
which left an empty string too. Both now yield an absent value, so the empty strings already in
base have to become absent as well: it is the same thing said in two ways, and only one of them
is falsy everywhere.

Normalizing the emails is also what keeps harvesting from duplicating them. It looks a contact
point up by its exact fields before creating one, and an empty string never matches the absent
value now extracted.

Contact points without a name also have no email and no contact form when they come from an
agent that carried nothing at all, which harvesting stopped creating in #3862. Nobody can be
reached through them and they render as an empty line under the datasets referencing them, so
they are removed rather than normalized.

Written against the collections rather than the models: this is a bulk rewrite of a few fields,
and loading every document through the ORM to save it back would only add ways to fail.
"""

import logging

log = logging.getLogger(__name__)

NO_INFORMATION = {"name": None, "email": None, "contact_form": None}


def migrate(db):
    for field in ("name", "email"):
        normalized = db.contact_point.update_many(
            {field: ""}, {"$unset": {field: ""}}
        ).modified_count
        log.info(f"{normalized} contact points had an empty {field} instead of no {field}.")

    unreachable = [
        contact_point["_id"] for contact_point in db.contact_point.find(NO_INFORMATION, {"_id": 1})
    ]
    if not unreachable:
        log.info("No contact point left without any way to reach it.")
        return

    for collection in (db.dataset, db.dataservice):
        detached = collection.update_many(
            {"contact_points": {"$in": unreachable}},
            {"$pull": {"contact_points": {"$in": unreachable}}},
        ).modified_count
        log.info(f"{detached} {collection.name}s no longer reference an unreachable contact point.")

    removed = db.contact_point.delete_many({"_id": {"$in": unreachable}}).deleted_count
    log.info(f"{removed} contact points removed, holding nothing but a role.")
