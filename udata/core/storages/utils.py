# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import hashlib
import mimetypes
import os
import zlib

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
        extension = ext if not extension else ext + '.' + extension

    return extension


def normalize(filename):
    return slugify(filename)
