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


class UrlFor(Raw):
    def __init__(self, endpoint, mapper=None, **kwargs):
        super(UrlFor, self).__init__(**kwargs)
        self.endpoint = endpoint
        self.mapper = mapper or self.default_mapper

    def default_mapper(self, obj):
        return {'id': str(obj.id)}

    def output(self, key, obj):
        return url_for(self.endpoint, _external=True, **self.mapper(obj))


class NextPageUrl(Raw):
    def output(self, key, obj):
        if not obj.has_next:
            return None
        args = request.args.copy()
        args['page'] = obj.page + 1
        return url_for(request.endpoint, _external=True, **args)


class PreviousPageUrl(Raw):
    def output(self, key, obj):
        if not obj.has_prev:
            return None
        args = request.args.copy()
        args['page'] = obj.page - 1
        return url_for(request.endpoint, _external=True, **args)


def pager(page_fields):
    pager_fields = {
        'data': api.as_list(Nested(page_fields, attribute='objects', description='The page data')),
        'page': Integer(description='The current page', required=True, min=0),
        'page_size': Integer(description='The page size used for pagination', required=True, min=0),
        'total': Integer(description='The total paginated items', required=True, min=0),
        'next_page': NextPageUrl(description='The next page URL if exists'),
        'previous_page': PreviousPageUrl(description='The previous page URL if exists'),
    }
    return pager_fields


def marshal_page(page, page_fields):
    return marshal(page, pager(page_fields))


def marshal_page_with(func):
    pass
