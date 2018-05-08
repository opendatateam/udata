# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from datetime import date, datetime
from dateutil.parser import parse

from mongoengine import EmbeddedDocument
from mongoengine.fields import BaseField, DateTimeField
from mongoengine.signals import pre_save

from udata.i18n import lazy_gettext as _


log = logging.getLogger(__name__)


class DateField(BaseField):
    '''
    Store date in iso format
    '''
    def to_python(self, value):
        if isinstance(value, date):
            return value
        try:
            value = parse(value, yearfirst=True).date()
        except:
            pass
        return value

    def to_mongo(self, value):
        if not value:
            return None
        return value.isoformat()

    def prepare_query_value(self, op, value):
        if isinstance(value, date):
            return value.isoformat()
        elif isinstance(value, datetime):
            return value.date.isoformat()
        return value

    def validate(self, value):
        if not isinstance(value, date):
            self.error('DateField only accepts date values')


class DateRange(EmbeddedDocument):
    start = DateField(required=True)
    end = DateField(required=True)

    def to_dict(self):
        return {'start': self.start, 'end': self.end}


class Datetimed(object):
    created_at = DateTimeField(verbose_name=_('Creation date'),
                               default=datetime.now, required=True)
    last_modified = DateTimeField(verbose_name=_('Last modification date'),
                                  default=datetime.now, required=True)


@pre_save.connect
def set_modified_datetime(sender, document, **kwargs):
    if isinstance(document, Datetimed):
        document.last_modified = datetime.now()
