import hashlib
import mimetypes
import os
import zlib

from flask import current_app
from slugify import Slugify

CHUNK_SIZE = 2 ** 16


slugify = Slugify(separator='-', to_lower=True, safe_chars='.')


def hash(file, hasher):
    blk_size_to_read = hasher.block_size * CHUNK_SIZE
    while (True):
        read_data = file.read(blk_size_to_read)
        if not read_data:
            break
        hasher.update(read_data)
    return hasher.hexdigest()


def sha1(file):
    '''Perform a SHA1 digest on file'''
    return hash(file, hashlib.sha1())


def md5(file):
    '''Perform a MD5 digest on a file'''
    return hash(file, hashlib.md5())


def crc32(file):
    '''Perform a CRC digest on a file'''
    value = zlib.crc32(file.read())
    return '%08X' % (value & 0xFFFFFFFF)


def mime(url):
    '''Get the mimetype from an url or a filename'''
    return mimetypes.guess_type(url)[0]


def extension(filename):
    '''Properly extract the extension from filename'''
    filename = os.path.basename(filename)
    extension = None

    while '.' in filename:
        filename, ext = os.path.splitext(filename)
        if ext.startswith('.'):
            ext = ext[1:]

        if extension and ext not in current_app.config['ALLOWED_RESOURCES_EXTENSIONS']:
            # We don't want to add this extension if one has already been detected
            # and this one is not in the allowed resources extensions list.
            break

        extension = ext if not extension else ext + '.' + extension

        if ext not in current_app.config['ALLOWED_ARCHIVED_EXTENSIONS']:
            # We don't want to continue the loop if this ext is not an allowed archived extension
            break

    return extension


def normalize(filename):
    return slugify(filename)
