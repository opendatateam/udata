import io
import os
from datetime import UTC, datetime

from flask import json
from werkzeug.datastructures import FileStorage

from udata.api import api, fields

from . import chunks, utils

META = "meta.json"

IMAGES_MIMETYPES = ("image/jpeg", "image/png", "image/webp")


uploaded_image_fields = api.model(
    "UploadedImage",
    {
        "success": fields.Boolean(
            description="Whether the upload succeeded or not.", readonly=True, default=True
        ),
        "image": fields.ImageField(),
    },
)

chunk_status_fields = api.model("UploadStatus", {"success": fields.Boolean, "error": fields.String})


image_parser = api.parser()
image_parser.add_argument("file", type=FileStorage, location="files")
image_parser.add_argument("bbox", type=str, location="form")


upload_parser = api.parser()
upload_parser.add_argument("file", type=FileStorage, location="files")
upload_parser.add_argument("uuid", type=str, location="form")
upload_parser.add_argument("filename", type=str, location="form")
upload_parser.add_argument("partindex", type=int, location="form")
upload_parser.add_argument("partbyteoffset", type=int, location="form")
upload_parser.add_argument("totalparts", type=int, location="form")
upload_parser.add_argument("chunksize", type=int, location="form")


class UploadStatus(Exception):
    def __init__(self, ok=True, error=None):
        super(UploadStatus, self).__init__()
        self.ok = ok
        self.error = error


class UploadProgress(UploadStatus):
    """Raised on successful chunk uploaded"""

    pass


class UploadError(UploadStatus):
    """Raised on any upload error"""

    def __init__(self, error=None):
        super(UploadError, self).__init__(ok=False, error=error)


def on_upload_status(status):
    """Not an error, just raised when chunk is processed"""
    if status.ok:
        return {"success": True}, 200
    else:
        return {"success": False, "error": status.error}, 400


@api.errorhandler(UploadStatus)
@api.errorhandler(UploadError)
@api.errorhandler(UploadProgress)
@api.marshal_with(chunk_status_fields, code=200)
def api_upload_status(status):
    """API Upload response handler"""
    return on_upload_status(status)


def chunk_filename(uuid, part):
    return os.path.join(str(uuid), str(part))


def get_file_size(file):
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)
    return size


def save_chunk(file, args):
    # Check file size
    if get_file_size(file) != args["chunksize"]:
        raise UploadProgress(ok=False, error="Chunk size mismatch")
    filename = chunk_filename(args["uuid"], args["partindex"])
    chunks.save(file, filename=filename)
    meta_filename = chunk_filename(args["uuid"], META)
    chunks.write(
        meta_filename,
        json.dumps(
            {
                "uuid": str(args["uuid"]),
                "filename": args["filename"],
                "totalparts": args["totalparts"],
                "lastchunk": datetime.now(UTC),
            }
        ),
        overwrite=True,
    )
    raise UploadProgress()


class ChunksReader(io.RawIOBase):
    """A read-only stream over the parts of a chunked upload, in order.

    Parts are fetched one at a time so a single chunk sits in memory at any
    point: the destination storage pulls from this stream instead of being
    handed the whole reassembled file.
    """

    def __init__(self, uuid, totalparts):
        self.uuid = uuid
        self.totalparts = totalparts
        self.next_part = 0
        self.buffer = b""

    def readable(self):
        return True

    def readinto(self, target):
        while not self.buffer and self.next_part < self.totalparts:
            self.buffer = chunks.read(chunk_filename(self.uuid, self.next_part))
            self.next_part += 1

        size = min(len(target), len(self.buffer))
        target[:size] = self.buffer[:size]
        self.buffer = self.buffer[size:]
        return size


def combine_chunks(storage, args, prefix=None):
    """
    Combine a chunked file into a whole file again.
    Streams every part, in order, into the destination storage.
    Chunks are stored in the chunks storage.

    Saving (rather than writing to an open file) is what applies the storage
    checks — the allowed extensions in particular — to chunked uploads too.
    """
    uuid = args["uuid"]
    # Normalize filename including extension
    target = utils.normalize(args["filename"])
    stream = io.BufferedReader(ChunksReader(uuid, args["totalparts"]))

    fs_filename = storage.save(stream, filename=target, prefix=prefix)

    # Chunks are dropped once the whole file made it to its destination, so a
    # failed combination can be retried instead of losing the upload.
    for part in range(args["totalparts"]):
        chunks.delete(chunk_filename(uuid, part))
    chunks.delete(chunk_filename(uuid, META))
    return fs_filename


def handle_upload(storage, prefix=None):
    args = upload_parser.parse_args()
    is_chunk = args["totalparts"] and args["totalparts"] > 1
    uploaded_file = args["file"]

    if is_chunk:
        if uploaded_file:
            save_chunk(uploaded_file, args)
        else:
            fs_filename = combine_chunks(storage, args, prefix=prefix)
    elif not uploaded_file:
        raise UploadError("Missing file parameter")
    else:
        # Normalize filename including extension
        filename = utils.normalize(uploaded_file.filename)
        fs_filename = storage.save(uploaded_file, prefix=prefix, filename=filename)

    metadata = storage.metadata(fs_filename)
    metadata["last_modified_internal"] = metadata.pop("modified")
    metadata["fs_filename"] = fs_filename
    checksum = metadata.pop("checksum")
    algo, checksum = checksum.split(":", 1)
    metadata[algo] = checksum
    metadata["format"] = utils.extension(fs_filename)
    return metadata


def parse_uploaded_image(field):
    """Parse an uploaded image and save into a ImageField()"""
    args = image_parser.parse_args()

    image = args["file"]
    if image.mimetype not in IMAGES_MIMETYPES:
        api.abort(400, "Unsupported image format")
    bbox = args.get("bbox", None)
    if bbox:
        bbox = [int(float(c)) for c in bbox.split(",")]
    field.save(image, bbox=bbox)
