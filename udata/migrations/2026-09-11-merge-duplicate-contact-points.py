"""
A contact point is looked up by its exact fields before a new one is created, so two identical
ones make the lookup itself fail with `MultipleObjectsReturned`: harvesting then rejects every
dataset naming them, and so does the API creating one.

`2026-08-21-clean-nameless-contact-points` is what made them identical. It turned the empty
names and emails into absent ones, and a contact point harvested between the deploy and that
migration was created with an absent name next to the one still holding the empty string it was
meant to match. Normalized afterwards, the two say exactly the same thing.

An absent field and a `null` one are the same value to a query, hence the same value here:
both answer the lookup, so both have to be grouped as one to be merged.

Written against the collections rather than the models, like the migration that caused this:
re-saving every referencing dataset through the ORM would only add ways to fail.
"""

import logging

log = logging.getLogger(__name__)

IDENTITY_FIELDS = ("name", "email", "contact_form", "role", "owner", "organization")

DUPLICATES = [
    {
        "$group": {
            "_id": {field: {"$ifNull": [f"${field}", None]} for field in IDENTITY_FIELDS},
            "ids": {"$push": "$_id"},
        }
    },
    {"$match": {"ids.1": {"$exists": True}}},
]


def migrate(db):
    merged = 0
    for group in db.contact_point.aggregate(DUPLICATES):
        # The oldest is the one the others repeat, and the one most documents already point at.
        kept, *duplicates = sorted(group["ids"])

        for collection in (db.dataset, db.dataservice):
            referencing = {"contact_points": {"$in": duplicates}}
            collection.update_many(referencing, {"$addToSet": {"contact_points": kept}})
            collection.update_many(referencing, {"$pullAll": {"contact_points": duplicates}})

        merged += db.contact_point.delete_many({"_id": {"$in": duplicates}}).deleted_count

    log.info(f"{merged} duplicate contact points merged into the one they repeat.")
