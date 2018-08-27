# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os

from datetime import datetime

from flask import json
from werkzeug.datastructures import FileStorage

from udata.api import api, fields

from . import utils, chunks


META = 'meta.json'


uploaded_image_fields = api.model('UploadedImage', {
    'success': fields.Boolean(
        description='Whether the upload succeeded or not.',
        readonly=True, default=True),
    'image': fields.ImageField(),
})

chunk_status_fields = api.model('UploadStatus', {
    'success': fields.Boolean,
    'error': fields.String
})


image_parser = api.parser()
image_parser.add_argument('file', type=FileStorage, location='files')
image_parser.add_argument('bbox', type=str, location='form')


upload_parser = api.parser()
upload_parser.add_argument('file', type=FileStorage, location='files')
upload_parser.add_argument('uuid', type=str, location='form')
upload_parser.add_argument('filename', type=unicode, location='form')
upload_parser.add_argument('partindex', type=int, location='form')
upload_parser.add_argument('partbyteoffset', type=int, location='form')
upload_parser.add_argument('totalparts', type=int, location='form')
upload_parser.add_argument('chunksize', type=int, location='form')


class UploadStatus(Exception):
    def __init__(self, ok=True, error=None):
        super(UploadStatus, self).__init__()
        self.ok = ok
        self.error = error


class UploadProgress(UploadStatus):
    '''Raised on successful chunk uploaded'''
    pass


class UploadError(UploadStatus):
    '''Raised on any upload error'''
    def __init__(self, error=None):
        super(UploadError, self).__init__(ok=False, error=error)


def on_upload_status(status):
    '''Not an error, just raised when chunk is processed'''
    if status.ok:
        return {'success': True}, 200
    else:
        return {'success': False, 'error': status.error}, 400


@api.errorhandler(UploadStatus)
@api.errorhandler(UploadError)
@api.errorhandler(UploadProgress)
@api.marshal_with(chunk_status_fields, code=200)
def api_upload_status(status):
    '''API Upload response handler'''
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
    if get_file_size(file) != args['chunksize']:
        raise UploadProgress(ok=False, error='Chunk size mismatch')
    filename = chunk_filename(args['uuid'], args['partindex'])
    chunks.save(file, filename=filename)
    meta_filename = chunk_filename(args['uuid'], META)
    chunks.write(meta_filename, json.dumps({
        'uuid': str(args['uuid']),
        'filename': args['filename'],
        'totalparts': args['totalparts'],
        'lastchunk': datetime.now(),
    }), overwrite=True)
    raise UploadProgress()


def combine_chunks(storage, args, prefix=None):
    '''
    Combine a chunked file into a whole file again.
    Goes through each part, in order,
    and appends that part's bytes to another destination file.
    Chunks are stored in the chunks storage.
    '''
    uuid = args['uuid']
    # Normalize filename including extension
    target = utils.normalize(args['filename'])
    if prefix:
        target = os.path.join(prefix, target)
    with storage.open(target, 'wb') as out:
        for i in xrange(args['totalparts']):
            partname = chunk_filename(uuid, i)
            out.write(chunks.read(partname))
            chunks.delete(partname)
    chunks.delete(chunk_filename(uuid, META))
    return target


def handle_upload(storage, prefix=None):
    args = upload_parser.parse_args()
    is_chunk = args['totalparts'] > 1
    uploaded_file = args['file']

    if is_chunk:
        if uploaded_file:
            save_chunk(uploaded_file, args)
        else:
            filename = combine_chunks(storage, args, prefix=prefix)
    elif not uploaded_file:
        raise UploadError('Missing file parameter')
    else:
        # Normalize filename including extension
        filename = utils.normalize(uploaded_file.filename)
        filename = storage.save(uploaded_file, prefix=prefix,
                                filename=filename)

    metadata = storage.metadata(filename)
    checksum = metadata.pop('checksum')
    algo, checksum = checksum.split(':', 1)
    metadata[algo] = checksum
    metadata['format'] = utils.extension(filename)
    return metadata


def parse_uploaded_image(field):
    '''Parse an uploaded image and save into a db.ImageField()'''
    args = image_parser.parse_args()

    image = args['file']
    bbox = args.get('bbox', None)
    if bbox:
        bbox = [int(float(c)) for c in bbox.split(',')]
    field.save(image, bbox=bbox)
