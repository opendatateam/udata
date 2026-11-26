"""
Leave no remote resource with a stored file.

Uploading onto a remote resource used to leave its filetype untouched, and the
follow-up metadata update setting `filetype: file` was rejected, leaving remote
resources pointing to a file on our storage, outside the hosted file protection.
Until opendatateam/udata#3254 a hosted file could also be switched to remote,
then given any url.

A resource whose url still targets its stored file is switched to file: it is
the only holder of that file, the links sharing it with another dataset resource
being unset by `2026-11-25-backfilled-links-unset-fs-filename.py`. A resource
whose url targets something else, or whose file is held by a community resource
(the 2020 backfill set a `fs_filename` on those links too), is a link: its
`fs_filename` is unset, the file is left untouched on the storage.

Community resources follow the same rule on their url: a reupload onto a remote
community resource left it remote too.
"""

import logging

log = logging.getLogger(__name__)


def migrate(db):
    community_fs_filenames = set(
        db.community_resource.distinct("fs_filename", {"fs_filename": {"$ne": None}})
    )
    switched = 0
    unset = 0
    datasets = db.dataset.find(
        {"resources": {"$elemMatch": {"filetype": "remote", "fs_filename": {"$ne": None}}}},
        {
            "resources._id": 1,
            "resources.filetype": 1,
            "resources.fs_filename": 1,
            "resources.url": 1,
        },
    )
    for dataset in datasets:
        for resource in dataset["resources"]:
            fs_filename = resource.get("fs_filename")
            if resource.get("filetype") != "remote" or not fs_filename:
                continue
            if fs_filename not in community_fs_filenames and (resource.get("url") or "").endswith(
                f"/{fs_filename}"
            ):
                update = {"$set": {"resources.$[resource].filetype": "file"}}
                log.info(
                    f"Switched to file: dataset {dataset['_id']}, resource {resource['_id']}, "
                    f"fs_filename {fs_filename}"
                )
                switched += 1
            else:
                update = {"$unset": {"resources.$[resource].fs_filename": ""}}
                log.info(
                    f"Unset fs_filename: dataset {dataset['_id']}, resource {resource['_id']}, "
                    f"fs_filename {fs_filename}, url {resource.get('url')}"
                )
                unset += 1
            db.dataset.update_one(
                {"_id": dataset["_id"]},
                update,
                array_filters=[{"resource._id": resource["_id"]}],
            )
    communities = db.community_resource.find(
        {"filetype": "remote", "fs_filename": {"$ne": None}}, {"fs_filename": 1, "url": 1}
    )
    for community in communities:
        fs_filename = community["fs_filename"]
        if (community.get("url") or "").endswith(f"/{fs_filename}"):
            update = {"$set": {"filetype": "file"}}
            log.info(
                f"Switched to file: community resource {community['_id']}, "
                f"fs_filename {fs_filename}"
            )
            switched += 1
        else:
            update = {"$unset": {"fs_filename": ""}}
            log.info(
                f"Unset fs_filename: community resource {community['_id']}, "
                f"fs_filename {fs_filename}, url {community.get('url')}"
            )
            unset += 1
        db.community_resource.update_one({"_id": community["_id"]}, update)
    log.info(f"{switched} resources switched to file.")
    log.info(f"{unset} resources kept remote with their fs_filename unset.")
