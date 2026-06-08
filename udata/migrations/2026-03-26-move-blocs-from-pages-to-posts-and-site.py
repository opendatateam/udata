"""
Move blocs from the intermediary Page model directly onto Post and Site.

Posts with body_type="blocs" referenced a Page via content_as_page.
Site referenced 3 Pages via datasets_page, reuses_page, dataservices_page.

This migration copies the blocs arrays from the referenced Page documents
directly into the Post/Site documents, then removes the Page references.
"""

import logging

log = logging.getLogger(__name__)


def migrate(db):
    post_collection = db["post"]
    page_collection = db["page"]
    site_collection = db["site"]

    # Move blocs from Page to Post
    posts_with_page = list(
        post_collection.find({"content_as_page": {"$ne": None}}, {"content_as_page": 1})
    )
    log.info(f"Processing {len(posts_with_page)} posts with content_as_page...")

    migrated_posts = 0
    for post in posts_with_page:
        page = page_collection.find_one({"_id": post["content_as_page"]})
        if page and page.get("blocs"):
            post_collection.update_one(
                {"_id": post["_id"]},
                {
                    "$set": {"blocs": page["blocs"]},
                    "$unset": {"content_as_page": ""},
                },
            )
            migrated_posts += 1
        else:
            post_collection.update_one(
                {"_id": post["_id"]},
                {"$unset": {"content_as_page": ""}},
            )
    log.info(f"\tMigrated blocs for {migrated_posts} posts")

    # Move blocs from Page to Site
    for site in site_collection.find():
        updates = {}
        unsets = {}
        for page_field, blocs_field in [
            ("datasets_page", "datasets_blocs"),
            ("reuses_page", "reuses_blocs"),
            ("dataservices_page", "dataservices_blocs"),
        ]:
            page_id = site.get(page_field)
            if page_id:
                page = page_collection.find_one({"_id": page_id})
                if page and page.get("blocs"):
                    updates[blocs_field] = page["blocs"]
                unsets[page_field] = ""

        ops = {}
        if updates:
            ops["$set"] = updates
        if unsets:
            ops["$unset"] = unsets
        if ops:
            site_collection.update_one({"_id": site["_id"]}, ops)
            log.info(f"\tMigrated blocs for site {site['_id']}: {list(updates.keys())}")

    result = page_collection.drop()
    log.info(f"\tDropped page collection: {result}")
