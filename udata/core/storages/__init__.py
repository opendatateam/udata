# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from uuid import uuid4

from flask.ext import fs

AUTHORIZED_TYPES = fs.AllExcept(fs.SCRIPTS + fs.EXECUTABLES)

resources = fs.Storage('resources', AUTHORIZED_TYPES)
avatars = fs.Storage('avatars', fs.IMAGES)
images = fs.Storage('images', fs.IMAGES)
chunks = fs.Storage('resources', AUTHORIZED_TYPES)


def default_image_basename(*args, **kwargs):
    uuid = str(uuid4()).replace('-', '')
    return '/'.join((uuid[:2], uuid[2:]))


def init_app(app):
    if not 'BUCKETS_PREFIX' in app.config:
        app.config['BUCKETS_PREFIX'] = '/s'
    fs.init_app(app, resources, avatars, images, chunks)
