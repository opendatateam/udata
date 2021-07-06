import logging

from dateutil.parser import parse

from flask import request, url_for
from flask_restplus.fields import *  # noqa

from udata.utils import multi_to_dict
from udata.uris import endpoint_for

log = logging.getLogger(__name__)


class ISODateTime(String):
    __schema_format__ = 'date-time'

    def format(self, value):
        if isinstance(value, str):
            value = parse(value)
        return value.isoformat()


class Markdown(String):
    __schema_format__ = 'markdown'


class UrlFor(String):
    def __init__(self, endpoint, mapper=None, **kwargs):
        super(UrlFor, self).__init__(**kwargs)
        self.endpoint = endpoint
        self.fallback_endpoint = kwargs.pop('fallback_endpoint', None)
        self.mapper = mapper or self.default_mapper

    def default_mapper(self, obj):
        return {'id': str(obj.id)}

    def output(self, key, obj, **kwargs):
        return endpoint_for(self.endpoint, self.fallback_endpoint, _external=True, **self.mapper(obj))


class NextPageUrl(String):
    def output(self, key, obj, **kwargs):
        if not getattr(obj, 'has_next', None):
            return None
        args = multi_to_dict(request.args)
        args.update(request.view_args)
        args['page'] = obj.page + 1
        return url_for(request.endpoint, _external=True, **args)


class PreviousPageUrl(String):
    def output(self, key, obj, **kwargs):
        if not getattr(obj, 'has_prev', None):
            return None
        args = multi_to_dict(request.args)
        args.update(request.view_args)
        args['page'] = obj.page - 1
        return url_for(request.endpoint, _external=True, **args)


class ImageField(String):
    def __init__(self, size=None, original=False, **kwargs):
        super(ImageField, self).__init__(**kwargs)
        self.original = original
        self.size = size

    def format(self, field):
        if not field:
            return
        elif self.original:
            return field.fs.url(field.original, external=True)
        elif self.size:
            return field(self.size, external=True)
        else:
            # This will respect max_size if defined
            return field.fs.url(field.filename, external=True)


def pager(page_fields):
    pager_fields = {
        'data': List(Nested(page_fields), attribute='objects',
                     description='The page data'),
        'page': Integer(description='The current page', required=True, min=1),
        'page_size': Integer(description='The page size used for pagination',
                             required=True, min=0),
        'total': Integer(description='The total paginated items',
                         required=True, min=0),
        'next_page': NextPageUrl(description='The next page URL if exists'),
        'previous_page': PreviousPageUrl(
            description='The previous page URL if exists'),
        'facets': Raw(description='Search facets results if any'),
    }
    return pager_fields
