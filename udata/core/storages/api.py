import os
from datetime import datetime
from io import BytesIO

from flask import json, request
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


def get_header(name, type_: type = str):
    """Get a header value, converting to the specified type."""
    value = request.headers.get(name)
    if value is None:
        raise UploadError(f"Missing required header: {name}")
    try:
        return type_(value)
    except (ValueError, TypeError):
        raise UploadError(f"Invalid value for header {name}: {value}")


def save_chunk(file, args):
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
                "lastchunk": datetime.utcnow(),
            }
        ),
        overwrite=True,
    )
    raise UploadProgress()


def combine_chunks(storage, args, prefix=None):
    """
    Combine a chunked file into a whole file again.
    Goes through each part, in order,
    and appends that part's bytes to another destination file.
    Chunks are stored in the chunks storage.
    """
    uuid = args["uuid"]
    # Normalize filename including extension
    target = utils.normalize(args["filename"])
    if prefix:
        target = os.path.join(prefix, target)
    with storage.open(target, "wb") as out:
        for i in range(args["totalparts"]):
            partname = chunk_filename(uuid, i)
            out.write(chunks.read(partname))
            chunks.delete(partname)
    chunks.delete(chunk_filename(uuid, META))
    return target


def handle_upload(storage, prefix=None):
    content_type = request.content_type or ""

    if content_type.startswith("application/octet-stream"):
        # Binary upload mode: raw bytes in body, metadata in headers.
        # This avoids an ambiguity in multipart parsing where a \r byte at the
        # end of a chunk can be confused with the \r\n boundary separator,
        # causing data corruption for files with Windows line endings (CRLF).
        filename = get_header("Upload-Filename")
        args = {
            "uuid": get_header("Upload-UUID"),
            "filename": filename,
            "partindex": get_header("Upload-Part-Index", int),
            "partbyteoffset": get_header("Upload-Part-Byte-Offset", int),
            "totalparts": get_header("Upload-Total-Parts", int),
            "chunksize": get_header("Upload-Chunk-Size", int),
        }
        uploaded_file = FileStorage(stream=BytesIO(request.get_data()), filename=filename)
    else:
        args = upload_parser.parse_args()
        uploaded_file = args["file"]

    is_chunk = args["totalparts"] and args["totalparts"] > 1

    if is_chunk:
        if uploaded_file:
            save_chunk(uploaded_file, args)
        else:
            fs_filename = combine_chunks(storage, args, prefix=prefix)
    elif not uploaded_file:
        raise UploadError("Missing file parameter")
    else:
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
    """Parse an uploaded image and save into a db.ImageField()"""
    args = image_parser.parse_args()

    image = args["file"]
    if image.mimetype not in IMAGES_MIMETYPES:
        api.abort(400, "Unsupported image format")
    bbox = args.get("bbox", None)
    if bbox:
        bbox = [int(float(c)) for c in bbox.split(",")]
    field.save(image, bbox=bbox)
