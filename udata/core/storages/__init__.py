from uuid import uuid4

import flask_storage as fs
from flask import current_app

AUTHORIZED_TYPES = fs.AllExcept(fs.SCRIPTS + fs.EXECUTABLES)


class ConfigurableAuthorizedTypes(object):
    def __contains__(self, value):
        return value in current_app.config["ALLOWED_RESOURCES_EXTENSIONS"]


CONFIGURABLE_AUTHORIZED_TYPES = ConfigurableAuthorizedTypes()


resources = fs.Storage("resources", CONFIGURABLE_AUTHORIZED_TYPES)
avatars = fs.Storage("avatars", fs.IMAGES)
logos = fs.Storage("logos", fs.IMAGES)
images = fs.Storage("images", fs.IMAGES)
chunks = fs.Storage("chunks", AUTHORIZED_TYPES)
references = fs.Storage("references", AUTHORIZED_TYPES)


def default_image_basename(*args, **kwargs):
    uuid = str(uuid4()).replace("-", "")
    return "/".join((uuid[:2], uuid[2:]))


def init_app(app):
    if "BUCKETS_PREFIX" not in app.config:
        app.config["BUCKETS_PREFIX"] = "/s"
    fs.init_app(app, resources, avatars, logos, images, chunks, references)
