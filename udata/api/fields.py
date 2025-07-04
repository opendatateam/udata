import datetime
import logging

import pytz
from dateutil.parser import parse
from flask import request, url_for

# Explicitly import all of flask_restx fields so they're available throughout the codebase as api.fields
from flask_restx.fields import Arbitrary as Arbitrary
from flask_restx.fields import Boolean as Boolean
from flask_restx.fields import ClassName as ClassName
from flask_restx.fields import Date as Date
from flask_restx.fields import DateTime as DateTime
from flask_restx.fields import Fixed as Fixed
from flask_restx.fields import Float as Float
from flask_restx.fields import FormattedString as FormattedString
from flask_restx.fields import Integer as Integer
from flask_restx.fields import List as List
from flask_restx.fields import MarshallingError as MarshallingError
from flask_restx.fields import MinMaxMixin as MinMaxMixin
from flask_restx.fields import Nested as Nested
from flask_restx.fields import NumberMixin as NumberMixin
from flask_restx.fields import Polymorph as Polymorph
from flask_restx.fields import Raw as Raw
from flask_restx.fields import String as String
from flask_restx.fields import StringMixin as StringMixin
from flask_restx.fields import Url as Url
from flask_restx.fields import Wildcard as Wildcard

from udata.utils import multi_to_dict

log = logging.getLogger(__name__)


class ISODateTime(String):
    __schema_format__ = "date-time"

    def format(self, value):
        if isinstance(value, str):
            value = parse(value)
        if (
            isinstance(value, datetime.date)
            and not isinstance(value, datetime.datetime)
            or value.tzinfo
        ):
            return value.isoformat()
        return pytz.utc.localize(value).isoformat()


class Markdown(String):
    __schema_format__ = "markdown"


class Permission(Boolean):
    def __init__(self, mapper=None, **kwargs):
        super(Permission, self).__init__(**kwargs)

    def format(self, field):
        return field.can()


class NextPageUrl(String):
    def output(self, key, obj, **kwargs):
        if not getattr(obj, "has_next", None):
            return None
        args = multi_to_dict(request.args)
        args.update(request.view_args)
        args["page"] = obj.page + 1
        return url_for(request.endpoint, _external=True, **args)


class PreviousPageUrl(String):
    def output(self, key, obj, **kwargs):
        if not getattr(obj, "has_prev", None):
            return None
        args = multi_to_dict(request.args)
        args.update(request.view_args)
        args["page"] = obj.page - 1
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
        "data": List(Nested(page_fields), attribute="objects", description="The page data"),
        "page": Integer(description="The current page", required=True, min=1),
        "page_size": Integer(description="The page size used for pagination", required=True, min=0),
        "total": Integer(description="The total paginated items", required=True, min=0),
        "next_page": NextPageUrl(description="The next page URL if exists"),
        "previous_page": PreviousPageUrl(description="The previous page URL if exists"),
    }
    return pager_fields
