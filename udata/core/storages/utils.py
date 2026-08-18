import hashlib
import mimetypes
import os
import zlib

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


def stored_file_infos(storage, fs_filename) -> dict:
    """Describe a file that was just written to `storage`.

    The storage is the one that digested the content, so it is also the one
    that says with which algorithm: a local file is read back and hashed,
    while an S3 object carries a checksum computed and verified by the server.
    """
    infos = storage.metadata(fs_filename)
    infos["last_modified_internal"] = infos.pop("modified")
    infos["fs_filename"] = fs_filename
    infos["format"] = extension(fs_filename)
    infos["mime"] = infos["mime"] or DEFAULT_MIME
    # Spread `algo:hash` as `{algo: hash}` so callers can tell which algorithm
    # the storage came up with. There is none when the backend cannot digest
    # what it holds — an S3 object stored in several parts before the backend
    # started asking for a checksum has nothing but its parts' digests.
    if checksum := infos.pop("checksum"):
        algo, value = checksum.split(":", 1)
        infos[algo] = value
    return infos
