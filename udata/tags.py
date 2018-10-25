# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import current_app
from slugify import slugify
from werkzeug.local import LocalProxy


MIN_TAG_LENGTH = LocalProxy(lambda: current_app.config['TAG_MIN_LENGTH'])
MAX_TAG_LENGTH = LocalProxy(lambda: current_app.config['TAG_MAX_LENGTH'])


def slug(value):
    return slugify(value.lower())


def normalize(value):
    value = slug(value)
    if len(value) < MIN_TAG_LENGTH:
        value = ''
    elif len(value) > MAX_TAG_LENGTH:
        value = value[:MAX_TAG_LENGTH]
    return value


def tags_list(value):
    return list(set(slug(tag) for tag in value.split(',') if tag.strip()))
