# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import current_app
from slugify import slugify


def slug(value):
    return slugify(value.lower())


def normalize(value):
    value = slug(value)
    min_length = current_app.config['TAG_MIN_LENGTH']
    max_length = current_app.config['TAG_MAX_LENGTH']
    if len(value) < min_length:
        value = ''
    elif len(value) > max_length:
        value = value[:max_length]
    return value


def tags_list(value):
    return list(set(slug(tag) for tag in value.split(',') if tag.strip()))
