import hashlib
import mimetypes
import os
import zlib
from datetime import UTC, datetime

from flask import current_app
from slugify import Slugify

CHUNK_SIZE = 2**16

# What a file whose extension tells us nothing is served as.
DEFAULT_MIME = "application/octet-stream"


slugify = Slugify(separator="-", to_lower=True, safe_chars=".")


def hash(file, hasher):
    blk_size_to_read = hasher.block_size * CHUNK_SIZE
    while True:
        read_data = file.read(blk_size_to_read)
        if not read_data:
            break
        hasher.update(read_data)
    return hasher.hexdigest()


def sha1(file):
    """Perform a SHA1 digest on file"""
    return hash(file, hashlib.sha1())


def md5(file):
    """Perform a MD5 digest on a file"""
    return hash(file, hashlib.md5())


def crc32(file):
    """Perform a CRC digest on a file"""
    value = zlib.crc32(file.read())
    return "%08X" % (value & 0xFFFFFFFF)


def mime(url):
    """Get the mimetype from an url or a filename"""
    return mimetypes.guess_type(url)[0]


def extension(filename):
    """
    Properly extract the extension from filename.
    We keep the last extension except for archive extensions, where we check
    previous extensions as well.
    If it is in ALLOWED_RESOURCES_EXTENSIONS, we add it to the extension.

    Some examples of extension detection:
    - test.unknown -> unknown
    - test.2022.zip -> zip
    - test.2022.csv.tar.gz -> csv.tar.gz
    - test.geojson.csv -> csv
    """
    filename = os.path.basename(filename)
    extension = None

    while "." in filename:
        filename, ext = os.path.splitext(filename)
        if ext.startswith("."):
            ext = ext[1:]

        if extension and ext not in current_app.config["ALLOWED_RESOURCES_EXTENSIONS"]:
            # We don't want to add this extension if one has already been detected
            # and this one is not in the allowed resources extensions list.
            break

        extension = ext if not extension else ext + "." + extension

        if ext not in current_app.config["ALLOWED_ARCHIVE_EXTENSIONS"]:
            # We don't want to continue the loop if this ext is not an allowed archived extension
            break

    return extension


def normalize(filename):
    return slugify(filename)


class MeasuredStream:
    """Wrap an upload stream to digest and size its content as it is read.

    The stream is handed to the storage, so the digest and the length describe
    exactly what was written, without a second pass over the file.
    """

    def __init__(self, stream):
        self.stream = stream
        self.hasher = hashlib.sha1()
        self.size = 0

    def read(self, size=-1):
        data = self.stream.read(size)
        self.hasher.update(data)
        self.size += len(data)
        return data

    @property
    def sha1(self):
        return self.hasher.hexdigest()


def stored_file_infos(storage, fs_filename, stream: MeasuredStream) -> dict:
    """Describe a file that was just written to `storage` out of `stream`.

    Everything is derived from the upload itself rather than read back from
    the backend: an S3 ETag is not a digest of the content once an object is
    uploaded in several parts, and the stored content type is only ever what
    the backend guessed when writing.
    """
    return {
        "url": storage.url(fs_filename, external=True),
        "fs_filename": fs_filename,
        "filename": os.path.basename(fs_filename),
        "size": stream.size,
        "sha1": stream.sha1,
        "mime": mime(fs_filename) or DEFAULT_MIME,
        "format": extension(fs_filename),
        "last_modified_internal": datetime.now(UTC),
    }
