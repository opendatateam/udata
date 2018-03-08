# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os

from werkzeug.datastructures import FileStorage

from udata.api import api, fields

from . import utils, chunks


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
@api.marshal_with(chunk_status_fields, code=200)
def api_upload_status(status):
    '''API Upload response handler'''
    return on_upload_status(status)


def save_chunk(file, args):
    filename = os.path.join(args['uuid'], str(args['partindex']))
    chunks.save(file, filename=filename)


def combine_chunks(args):
    '''
    Combine a chunked file into a whole file again.
    Goes through each part, in order,
    and appends that part's bytes to another destination file.
    Chunks are stored in the chunks storage.
    '''
    prefix = args['uuid']
    filename = os.path.join(prefix, args['filename'])
    chunks.write(filename, '')
    with chunks.open(filename, 'wb+') as out:
        for i in xrange(args['totalparts']):
            partname = os.path.join(prefix, str(i))
            out.write(chunks.read(partname))
    return FileStorage(chunks.open(filename, 'rb'), args['filename'])


def handle_upload(storage, prefix=None):
    args = upload_parser.parse_args()
    is_chunk = args['totalparts'] > 1
    uploaded_file = args['file']

    if is_chunk:
        if uploaded_file:
            save_chunk(uploaded_file, args)
            raise UploadProgress()
        else:
            uploaded_file = combine_chunks(args)
    elif not uploaded_file:
        raise UploadError('Missing file parameter')

    filename = storage.save(uploaded_file, prefix=prefix)
    uploaded_file.seek(0)
    size = os.path.getsize(storage.path(filename)) if storage.root else None
    return {
        'url': storage.url(filename, True),
        'filename': filename,
        'sha1': utils.sha1(uploaded_file),
        'size': size,
        'mime': utils.mime(filename),
        'format': utils.extension(filename),
    }


def parse_uploaded_image(field):
    '''Parse an uploaded image and save into a db.ImageField()'''
    args = image_parser.parse_args()

    image = args['file']
    bbox = args.get('bbox', None)
    if bbox:
        bbox = [int(float(c)) for c in bbox.split(',')]
    field.save(image, bbox=bbox)
