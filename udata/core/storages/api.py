import io
import os
import uuid
from datetime import UTC, datetime

from flask import json
from lxml import etree
from PIL import Image, UnidentifiedImageError
from werkzeug.datastructures import FileStorage

from udata.api import API, api, fields

from . import chunks, images, utils

META = "meta.json"

IMAGES_FORMATS = ("JPEG", "PNG", "WEBP")

# Where the images shown in a content (a bloc, a markdown text) are stored, in the images
# storage. Purged once nothing shows them anymore, see `purge_content_images`.
CONTENT_IMAGES_PREFIX = "content"
# Large for an illustration.
CONTENT_IMAGE_MAX_SIZE = 5 * 1024 * 1024

ns = api.namespace("images", "Images shown in a content")


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
image_parser.add_argument(
    "file", type=FileStorage, location="files", required=True, help="The image to upload"
)
image_parser.add_argument(
    "bbox",
    type=str,
    location="form",
    help="An optional crop box, as `left,upper,right,lower` pixel coordinates",
)


upload_parser = api.parser()
upload_parser.add_argument(
    "file",
    type=FileStorage,
    location="files",
    help="The file to upload, or the part to upload when the file is sent in chunks. "
    "Only the request assembling a chunked upload omits it.",
)
upload_parser.add_argument(
    "uuid",
    type=str,
    location="form",
    help="Chunked uploads only: an identifier chosen by the client, shared by every "
    "request of the same upload",
)
upload_parser.add_argument(
    "filename",
    type=str,
    location="form",
    help="Chunked uploads only: the name of the assembled file. A single-request upload "
    "takes it from the uploaded file itself.",
)
upload_parser.add_argument(
    "partindex",
    type=int,
    location="form",
    help="Chunked uploads only: the zero-based index of the part being sent",
)
upload_parser.add_argument(
    "totalparts",
    type=int,
    location="form",
    help="The number of parts the file is split into. Above 1, the upload is chunked: "
    "send each part, then a last request without `file` to assemble them.",
)
upload_parser.add_argument(
    "chunksize",
    type=int,
    location="form",
    help="Chunked uploads only: the size in bytes of the part being sent, checked "
    "against the received one",
)


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


def discard_chunks(uuid, totalparts):
    for part in range(totalparts):
        chunks.delete(chunk_filename(uuid, part))
    chunks.delete(chunk_filename(uuid, META))


def handle_upload(storage, prefix=None):
    args = upload_parser.parse_args()
    is_chunk = args["totalparts"] and args["totalparts"] > 1
    uploaded_file = args["file"]

    if is_chunk:
        if uploaded_file:
            # Raises UploadProgress: a part was stored, the file is incomplete.
            save_chunk(uploaded_file, args)
        # Normalize filename including extension
        filename = utils.normalize(args["filename"])
        source = io.BufferedReader(ChunksReader(args["uuid"], args["totalparts"]))
    elif not uploaded_file:
        raise UploadError("Missing file parameter")
    else:
        # Normalize filename including extension
        filename = utils.normalize(uploaded_file.filename)
        source = uploaded_file

    infos = utils.save_upload(storage, source, filename, prefix=prefix)

    if is_chunk:
        # Chunks are dropped once the whole file made it to its destination, so
        # a failed combination can be retried instead of losing the upload.
        discard_chunks(args["uuid"], args["totalparts"])

    return infos


def parse_bbox(raw: str, image_size: tuple[int, int]) -> list[int]:
    """Parse a crop box given by the client as `left,upper,right,lower` pixel coordinates"""
    coordinates = raw.split(",")
    if len(coordinates) != 4:
        api.abort(400, "Invalid bounding box")
    try:
        # `float` accepts values that `int` then refuses, such as `nan` or `1e400`.
        left, upper, right, lower = (int(float(coordinate)) for coordinate in coordinates)
    except (ValueError, OverflowError):
        api.abort(400, "Invalid bounding box")

    width, height = image_size
    # Pillow crops outside of the image instead of failing, padding the result: a box a
    # few digits wider than the source is enough to allocate hundreds of megabytes, then
    # to raise a decompression bomb error once past its pixel limit.
    if not (0 <= left < right <= width and 0 <= upper < lower <= height):
        api.abort(400, "Bounding box outside of the image")

    return [left, upper, right, lower]


def uploaded_image_format(file) -> str | None:
    """The format of an uploaded image, as Pillow reads it, `None` when Pillow does not read
    the file.

    The mimetype is declared by the client and may not match the content at all (an SVG
    announced as `image/png` for instance): decode the file to know what it really is,
    otherwise Pillow raises further down and the request 500s.
    """
    try:
        with Image.open(file) as image:
            image_format = image.format
    except UnidentifiedImageError:
        return None
    except Image.DecompressionBombError:
        # A valid image whose header announces more pixels than Pillow accepts to decode.
        # A few dozen bytes are enough to declare a huge size, so this must be refused
        # here: every other decoding (resize, optimize, thumbnails) would raise too.
        api.abort(400, "Image is too large")
    finally:
        # `Image.open` left the cursor right after the header it read. The file may be stored
        # as-is afterwards (flask_storage only rewinds when it resizes or optimizes), which
        # would silently truncate it.
        file.seek(0)
    # A JPEG holding several pictures, as most phone cameras write them.
    return "JPEG" if image_format == "MPO" else image_format


def parse_uploaded_image(field):
    """Parse an uploaded image and save into a ImageField()"""
    args = image_parser.parse_args()

    image = args["file"]
    if uploaded_image_format(image) not in IMAGES_FORMATS:
        api.abort(400, "Unsupported image format")

    if args["bbox"]:
        with Image.open(image) as uploaded:
            bbox = parse_bbox(args["bbox"], uploaded.size)
        image.seek(0)
    else:
        bbox = None

    field.save(image, bbox=bbox)


content_image_parser = api.parser()
content_image_parser.add_argument(
    "file", type=FileStorage, location="files", required=True, help="The image to upload"
)

uploaded_content_image_fields = api.model(
    "UploadedContentImage",
    {"url": fields.String(description="The URL to show the image at", readonly=True)},
)


def is_svg(file) -> bool:
    # Only the root element is read: building the whole tree of a flat document of a hundred
    # megabytes takes gigabytes. Neither entities nor the network: a document cannot make the
    # parser read a local file, reach a server, or expand into gigabytes.
    events = etree.iterparse(
        file, events=("start",), resolve_entities=False, no_network=True, huge_tree=False
    )
    try:
        _, root = next(events)
    except (etree.XMLSyntaxError, StopIteration):
        return False
    return etree.QName(root).localname == "svg"


def content_image_extension(file) -> str:
    """The extension to store an uploaded image with, from what it really is: the name and the
    mimetype sent by the client prove nothing."""
    image_format = uploaded_image_format(file)
    if image_format in IMAGES_FORMATS:
        return image_format.lower()
    # Illustrations are often vector drawings, which Pillow does not read. Opened on their own,
    # they run the scripts they may hold: on S3, where the images are stored in production,
    # flask-storage stores them as attachments, downloaded rather than displayed.
    if image_format is None and is_svg(file):
        return "svg"
    api.abort(400, "Unsupported image format")


@ns.route("/", endpoint="content_images")
class ContentImagesAPI(API):
    @api.secure
    @api.doc("upload_content_image")
    @api.expect(content_image_parser)
    @api.marshal_with(uploaded_content_image_fields, code=201)
    def post(self):
        """Upload an image to show in a content, such as a bloc or a markdown text"""
        file = content_image_parser.parse_args()["file"]
        # Before reading it: whatever its format, decoding a file costs memory with its size.
        if get_file_size(file) > CONTENT_IMAGE_MAX_SIZE:
            api.abort(400, "Image is too large")
        extension = content_image_extension(file)
        file.seek(0)
        filename = images.save(
            file, filename=f"{uuid.uuid4().hex}.{extension}", prefix=CONTENT_IMAGES_PREFIX
        )
        return {"url": images.url(filename, external=True)}, 201
