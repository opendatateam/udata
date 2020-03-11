from datetime import date, timedelta

from udata.models import db


__all__ = ('WithMetrics',)


class WithMetrics(object):
    metrics = db.DictField()

