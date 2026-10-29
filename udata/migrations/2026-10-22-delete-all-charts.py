"""
Delete all Chart visualizations: the declarative config fields are
removed from the model and charts are a hidden beta, so existing documents are
dropped rather than migrated.

Deletion is done at the collection level, reading the image fields raw:
legacy documents may predate the current model shape and must not be
unmarshalled (or validated) to be deleted.
"""

import logging

log = logging.getLogger(__name__)

COLLECTION = "chart"
IMAGE_FIELDS = ("filename", "original")


def _delete_image_files(db):
    """Best-effort removal of the stored image files, from raw fields only."""
    from udata.core.storages import images

    for doc in db[COLLECTION].find({}, {"image": 1}):
        image = doc.get("image") or {}
        filenames = [image.get(field) for field in IMAGE_FIELDS]
        thumbnails = image.get("thumbnails") or {}
        filenames.extend(thumbnails.values())
        for filename in filter(None, filenames):
            try:
                if filename in images:
                    images.delete(filename)
            except Exception:
                log.exception("Failed to delete image file %s", filename)


def migrate(db):
    log.info("Deleting all Chart visualizations...")

    _delete_image_files(db)
    deleted_count = db[COLLECTION].delete_many({}).deleted_count
    log.info(f"Deleted {deleted_count} charts")
