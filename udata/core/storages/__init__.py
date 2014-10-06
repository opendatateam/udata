# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask.ext import fs

AUTHORIZED_TYPES = fs.AllExcept(fs.SCRIPTS + fs.EXECUTABLES)

resources = fs.Storage('resources', AUTHORIZED_TYPES)
avatars = fs.Storage('avatars', fs.IMAGES)
images = fs.Storage('images', fs.IMAGES)
chunks = fs.Storage('resources', AUTHORIZED_TYPES)


def init_app(app):
    if not 'BUCKETS_PREFIX' in app.config:
        app.config['BUCKETS_PREFIX'] = '/s'
    fs.init_app(app, resources, avatars, images, chunks)
