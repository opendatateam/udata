# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from werkzeug.datastructures import FileStorage

from udata.api import api, fields


uploaded_image_fields = api.model('UploadedImage', {
    'success': fields.Boolean(
        description='Whether the upload succeeded or not.',
        readonly=True, default=True),
    'image': fields.ImageField(),
})


image_parser = api.parser()
image_parser.add_argument('file', type=FileStorage, location='files')
image_parser.add_argument('bbox', type=str, location='form')


def parse_uploaded_image(field):
    '''Parse an uploaded image and save into a db.ImageField()'''
    args = image_parser.parse_args()

    image = args['file']
    bbox = args.get('bbox', None)
    if bbox:
        bbox = [int(float(c)) for c in bbox.split(',')]
    field.save(image, bbox=bbox)
