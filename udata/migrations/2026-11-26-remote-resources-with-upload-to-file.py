"""
Mark as hosted files the remote resources that received an upload.

Uploading onto a remote resource used to leave its filetype untouched, and the
follow-up metadata update setting `filetype: file` was rejected, leaving remote
resources pointing to a file on our storage, outside the hosted file protection.
Only resources whose url still targets their stored file are switched: an
unprotected url may have been edited since the upload, and switching would lock
a foreign url.
"""

import logging

from mongoengine.connection import get_db

log = logging.getLogger(__name__)


def migrate(db):
    db = get_db()
    switched = 0
    kept = 0
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
            if not (resource.get("url") or "").endswith(f"/{fs_filename}"):
                kept += 1
                continue
            db.dataset.update_one(
                {"_id": dataset["_id"]},
                {"$set": {"resources.$[resource].filetype": "file"}},
                array_filters=[{"resource._id": resource["_id"]}],
            )
            switched += 1
    log.info(f"{switched} resources switched to file.")
    log.info(f"{kept} resources kept remote: their url no longer targets their stored file.")
