import logging
from datetime import date, datetime

from dateutil.parser import parse
from mongoengine import EmbeddedDocument
from mongoengine.fields import BaseField, DateTimeField
from mongoengine.signals import pre_save

from udata.api_fields import field
from udata.i18n import lazy_gettext as _

log = logging.getLogger(__name__)


class DateField(BaseField):
    """
    Store date in iso format
    """

    def to_python(self, value):
        if isinstance(value, date):
            return value
        try:
            value = parse(value, yearfirst=True).date()
        except Exception:
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
            self.error("DateField only accepts date values")


class DateRange(EmbeddedDocument):
    start = DateField()
    end = DateField()

    def to_dict(self):
        return {"start": self.start, "end": self.end}

    def clean(self):
        if self.start and self.end and self.start > self.end:
            self.start, self.end = self.end, self.start


class Datetimed(object):
    created_at = field(
        DateTimeField(verbose_name=_("Creation date"), default=datetime.utcnow, required=True),
        sortable="created",
        readonly=True,
    )
    last_modified = field(
        DateTimeField(
            verbose_name=_("Last modification date"), default=datetime.utcnow, required=True
        ),
        sortable=True,
        readonly=True,
    )


@pre_save.connect
def set_modified_datetime(sender, document, **kwargs):
    changed = document._get_changed_fields()
    if isinstance(document, Datetimed) and "last_modified" not in changed:
        document.last_modified = datetime.utcnow()
