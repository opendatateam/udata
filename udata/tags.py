from flask import current_app
from slugify import slugify
from werkzeug.local import LocalProxy

TAG_MIN_LENGTH = LocalProxy(lambda: current_app.config["TAG_MIN_LENGTH"])
TAG_MAX_LENGTH = LocalProxy(lambda: current_app.config["TAG_MAX_LENGTH"])


def slug(value: str) -> str:
    return slugify(value.lower())


def normalize(value: str) -> str:
    value = slug(value)
    if len(value) < TAG_MIN_LENGTH:
        value = ""
    elif len(value) > TAG_MAX_LENGTH:
        value = value[:TAG_MAX_LENGTH]
    return value


def tags_list(value: str) -> list:
    return list(set(slug(tag) for tag in value.split(",") if tag.strip()))
