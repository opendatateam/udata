# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging

from collections import Iterable

from flask_mongoengine import Document

from .queryset import UDataQuerySet

log = logging.getLogger(__name__)


def serialize(value):
    if hasattr(value, 'to_dict'):
        return value.to_dict()
    elif isinstance(value, Iterable) and not isinstance(value, basestring):
        return [serialize(val) for val in value]
    else:
        return value


class UDataDocument(Document):
    meta = {
        'abstract': True,
        'queryset_class': UDataQuerySet,
    }

    def to_dict(self, exclude=None):
        excluded_keys = set(exclude or [])
        excluded_keys.add('_cls')
        return dict((
            (key, serialize(value))
            for key, value in self.to_mongo().items()
            if key not in excluded_keys
        ))


class DomainModel(UDataDocument):
    '''Placeholder for inheritance'''
    pass
