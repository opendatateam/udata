# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from os.path import join

from flaskext.uploads import UploadSet, AllExcept, SCRIPTS, EXECUTABLES, IMAGES, configure_uploads

AUTHORIZED_TYPES = AllExcept(SCRIPTS + EXECUTABLES)

resources_storage = UploadSet('resources', AUTHORIZED_TYPES)
avatars_storage = UploadSet('avatars', IMAGES)
images_storage = UploadSet('images', IMAGES)


def init_app(app):
    app.config.setdefault('UPLOADS_DEFAULT_DEST', join(app.instance_path, 'uploads'))
    configure_uploads(app, (resources_storage, avatars_storage, images_storage))
