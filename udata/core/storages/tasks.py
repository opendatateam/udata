import re
from datetime import UTC, datetime, timedelta

from bson import json_util
from dateutil.parser import parse
from flask import current_app, json

from udata.core.edito_blocs.models import SITE_BLOCS_FIELDS
from udata.core.organization.models import Organization
from udata.core.post.models import Post
from udata.core.site.models import Site
from udata.core.storages import chunks, images
from udata.core.storages.api import CONTENT_IMAGES_PREFIX, META
from udata.tasks import get_logger, job

log = get_logger(__name__)

CONTENT_IMAGE = re.compile(rf"{CONTENT_IMAGES_PREFIX}/[0-9a-f]{{32}}\.[a-z]+")

# The fields whose content may show an uploaded image. A content taking uploaded images must be
# listed here, otherwise its images are purged.
CONTENT_IMAGES_SOURCES = (
    (Post, ("content", "blocs")),
    (Organization, ("presentation_blocs",)),
    (Site, SITE_BLOCS_FIELDS),
)


@job("purge-chunks")
def purge_chunks(self):
    log.info("Purging uploaded chunks")
    max_retention = timedelta(seconds=current_app.config["UPLOAD_MAX_RETENTION"])
    meta_files = (f for f in chunks.list_files() if f.endswith(META))
    for filename in meta_files:
        metadata = json.loads(chunks.read(filename))
        if datetime.now(UTC) - parse(metadata["lastchunk"]) >= max_retention:
            uuid = metadata["uuid"]
            log.info("Removing %s expired chunks", uuid)
            chunks.delete(uuid)


def shown_content_images() -> set[str]:
    """The content images still shown somewhere, by their name in the images storage.

    Looked for in the whole stored contents rather than in the fields meant for an image: the URL
    of an image may also have been copied in a markdown text.
    """
    shown = set()
    for model, fields in CONTENT_IMAGES_SOURCES:
        for document in model._get_collection().find({}, dict.fromkeys(fields, 1)):
            shown.update(CONTENT_IMAGE.findall(json_util.dumps(document)))
    return shown


@job("purge-content-images")
def purge_content_images(self):
    """Delete the content images that nothing shows anymore: replaced, removed with their bloc
    or their page, or uploaded in an editor left without saving."""
    log.info("Purging the content images nothing shows")
    # Long enough for an image uploaded in an editor still open to be saved in its content.
    max_retention = timedelta(seconds=current_app.config["UPLOAD_MAX_RETENTION"])
    shown = shown_content_images()
    for filename in images.list_files():
        if not filename.startswith(f"{CONTENT_IMAGES_PREFIX}/") or filename in shown:
            continue
        # The local backend gives a naive local time, S3 an UTC one.
        modified = images.metadata(filename)["modified"].astimezone(UTC)
        if datetime.now(UTC) - modified >= max_retention:
            log.info("Removing content image %s", filename)
            images.delete(filename)
