# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import date
from uuid import uuid4

from flask.ext import fs

AUTHORIZED_TYPES = fs.AllExcept(fs.SCRIPTS + fs.EXECUTABLES)


def tmp_upload_to():
    uuid = str(uuid4()).replace('-', '')
    isodate = date.today().isoformat()
    return '/'.join((isodate, uuid))

resources = fs.Storage('resources', AUTHORIZED_TYPES)
avatars = fs.Storage('avatars', fs.IMAGES)
images = fs.Storage('images', fs.IMAGES)
chunks = fs.Storage('resources', AUTHORIZED_TYPES)
tmp = fs.Storage('tmp', fs.ALL, upload_to=tmp_upload_to)


def default_image_basename(*args, **kwargs):
    uuid = str(uuid4()).replace('-', '')
    return '/'.join((uuid[:2], uuid[2:]))


def init_app(app):
    if 'BUCKETS_PREFIX' not in app.config:
        app.config['BUCKETS_PREFIX'] = '/s'
    fs.init_app(app, resources, avatars, images, chunks, tmp)
