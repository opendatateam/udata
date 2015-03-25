# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from flask import request, url_for
from flask.ext.restplus.fields import *

from . import api


log = logging.getLogger(__name__)


@api.model(type='string', format='date-time')
class ISODateTime(Raw):
    def format(self, value):
        return value.isoformat()


@api.model(type='string', format='markdown')
class Markdown(String):
    pass


@api.model(type='string')
class UrlFor(Raw):
    def __init__(self, endpoint, mapper=None, **kwargs):
        super(UrlFor, self).__init__(**kwargs)
        self.endpoint = endpoint
        self.mapper = mapper or self.default_mapper

    def default_mapper(self, obj):
        return {'id': str(obj.id)}

    def output(self, key, obj):
        return url_for(self.endpoint, _external=True, **self.mapper(obj))


@api.model(type='string')
class NextPageUrl(String):
    def output(self, key, obj):
        if not obj.has_next:
            return None
        args = request.args.copy()
        args.update(request.view_args)
        args['page'] = obj.page + 1
        return url_for(request.endpoint, _external=True, **args)


@api.model(type='string')
class PreviousPageUrl(String):
    def output(self, key, obj):
        if not obj.has_prev:
            return None
        args = request.args.copy()
        args.update(request.view_args)
        args['page'] = obj.page - 1
        return url_for(request.endpoint, _external=True, **args)


class ImageField(Raw):
    def __init__(self, size=None, **kwargs):
        super(ImageField, self).__init__(**kwargs)
        self.size = size

    def format(self, field):
        return field(self.size, external=True) if self.size else field(external=True)


def pager(page_fields):
    pager_fields = {
        'data': api.as_list(Nested(page_fields, attribute='objects', description='The page data')),
        'page': Integer(description='The current page', required=True, min=1),
        'page_size': Integer(description='The page size used for pagination', required=True, min=0),
        'total': Integer(description='The total paginated items', required=True, min=0),
        'next_page': NextPageUrl(description='The next page URL if exists'),
        'previous_page': PreviousPageUrl(description='The previous page URL if exists'),
    }
    return pager_fields


base_reference = api.model('BaseReference', {
    'id': String(description='The object unique identifier', required=True),
    'class': ClassName(description='The object class', discriminator=True, required=True),
}, description='Base model for reference field, aka. inline model reference')
