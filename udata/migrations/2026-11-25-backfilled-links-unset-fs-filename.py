"""
Remove the `fs_filename` of remote resources linking to another resource's file.

The 2020 backfill (`2020-08-24-add-fs-filename.py`) set a `fs_filename` on every
resource whose url targets our storage, links to another resource's file
included. A resource's file is deleted from storage when the resource is deleted
or receives a new upload, so deleting such a link deleted the file of the
resource it links to.

A link is recognized by its `fs_filename` being carried by several dataset
resources: an upload stores each file under a unique name.
"""

import logging

log = logging.getLogger(__name__)


def migrate(db):
    shared_fs_filenames = [
        group["_id"]
        for group in db.dataset.aggregate(
            [
                {"$unwind": "$resources"},
                {"$match": {"resources.fs_filename": {"$ne": None}}},
                {"$group": {"_id": "$resources.fs_filename", "count": {"$sum": 1}}},
                {"$match": {"count": {"$gt": 1}}},
            ]
        )
    ]
    log.info(f"{len(shared_fs_filenames)} fs_filenames shared by several resources.")
    links = {"filetype": "remote", "fs_filename": {"$in": shared_fs_filenames}}
    link_count = 0
    for dataset in db.dataset.find(
        {"resources": {"$elemMatch": links}},
        {"resources._id": 1, "resources.filetype": 1, "resources.fs_filename": 1},
    ):
        for resource in dataset["resources"]:
            if resource.get("filetype") == "remote" and resource.get("fs_filename") in (
                shared_fs_filenames
            ):
                log.info(
                    f"Unset fs_filename: dataset {dataset['_id']}, resource {resource['_id']}, "
                    f"fs_filename {resource['fs_filename']}"
                )
                link_count += 1
    result = db.dataset.update_many(
        {"resources": {"$elemMatch": links}},
        {"$unset": {"resources.$[link].fs_filename": ""}},
        array_filters=[{f"link.{key}": value for key, value in links.items()}],
    )
    log.info(f"{link_count} links in {result.modified_count} datasets processed.")
