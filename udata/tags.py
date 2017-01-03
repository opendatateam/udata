# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from slugify import slugify

MIN_TAG_LENGTH = 3
MAX_TAG_LENGTH = 32


def slug(value):
    return slugify(value.lower())


def normalize(value):
    value = slug(value)
    if len(value) < MIN_TAG_LENGTH:
        value = ''
    elif MAX_TAG_LENGTH < len(value):
        value = value[:MAX_TAG_LENGTH]
    return value


def tags_list(value):
    return list(set(slug(tag) for tag in value.split(',') if tag.strip()))
