"""
Give each stored file a single hosted resource.

Two uploads of the same file name in the same dataset at the same second got the
same key: the second overwrote the first and both resources held the same
`fs_filename`, so deleting or replacing one deleted the file of the other.

The oldest resource of a dataset not deleted stays local (`purge_datasets`
deletes the files of a deleted dataset), the others become remote resources
pointing to it. A file also held by a community resource stays with it, every
dataset resource becomes remote. The overwritten contents cannot be recovered.
"""

import logging

log = logging.getLogger(__name__)


def migrate(db):
    shared = {
        group["_id"]: group["holders"]
        for group in db.dataset.aggregate(
            [
                {"$unwind": "$resources"},
                {"$match": {"resources.filetype": "file", "resources.fs_filename": {"$ne": None}}},
                {
                    "$group": {
                        "_id": "$resources.fs_filename",
                        "holders": {
                            "$push": {
                                "dataset": "$_id",
                                "deleted": {"$ifNull": ["$deleted", None]},
                                "resource": "$resources._id",
                                "created": "$resources.created_at_internal",
                            }
                        },
                    }
                },
                {"$match": {"holders.1": {"$exists": True}}},
            ]
        )
    }
    log.info(f"{len(shared)} stored files held by several hosted resources.")
    community_fs_filenames = set(
        db.community_resource.distinct("fs_filename", {"fs_filename": {"$in": list(shared)}})
    )

    remotes = 0
    for fs_filename, holders in shared.items():
        holders.sort(key=lambda h: (h["deleted"] is not None, h["created"], str(h["resource"])))
        if fs_filename in community_fs_filenames:
            local = None
            log.info(f"Kept by a community resource: fs_filename {fs_filename}")
        else:
            local, *_ = holders
            log.info(
                f"Stays local: dataset {local['dataset']}, resource {local['resource']}, "
                f"fs_filename {fs_filename}"
            )
        for holder in holders:
            if holder is local:
                continue
            db.dataset.update_one(
                {"_id": holder["dataset"]},
                {
                    "$set": {"resources.$[link].filetype": "remote"},
                    "$unset": {"resources.$[link].fs_filename": ""},
                },
                array_filters=[{"link._id": holder["resource"]}],
            )
            log.info(
                f"Turned remote: dataset {holder['dataset']}, resource {holder['resource']}, "
                f"fs_filename {fs_filename}"
            )
            remotes += 1
    log.info(f"{remotes} resources turned remote.")
