"""
Leave no remote resource with a stored file.

Uploading onto a remote resource used to leave its filetype untouched, and the
follow-up metadata update setting `filetype: file` was rejected, leaving remote
resources pointing to a file on our storage, outside the hosted file protection.
Until opendatateam/udata#3254 a hosted file could also be switched to remote,
then given any url.

A resource whose url still targets its stored file is switched to file: it is
the only holder of that file, the links sharing it with another resource being
unset by `2026-11-25-backfilled-links-unset-fs-filename.py`. A resource whose
url targets something else is a link: its `fs_filename` is unset, the file is
left untouched on the storage.
"""

import logging

log = logging.getLogger(__name__)


def migrate(db):
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
            if (resource.get("url") or "").endswith(f"/{fs_filename}"):
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
    log.info(f"{switched} resources switched to file.")
    log.info(f"{unset} resources kept remote with their fs_filename unset.")
