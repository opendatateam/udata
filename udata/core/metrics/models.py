# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import date, timedelta

from udata.models import db


__all__ = ('Metrics', 'WithMetrics')


class MetricsQuerySet(db.BaseQuerySet):
    def _today(self):
        return date.today()

    def get_for(self, obj, days=1):
        object_id = obj.id if hasattr(obj, 'id') else obj
        days = max(days or 1, 1)
        first_day = (date.today() - timedelta(days)).isoformat()
        return self(object_id=object_id, level='daily', date__gt=first_day)

    def last_for(self, obj):
        return self.get_for(obj=obj).order_by('-date').first()

    def update_daily(self, obj, date=None, **kwargs):
        oid = obj.id if hasattr(obj, 'id') else obj
        if isinstance(date, basestring):
            day = date
        else:
            day = (date or self._today()).isoformat()
        commands = dict(('set__values__{0}'.format(k), v) for k, v in kwargs.items())
        return Metrics.objects(object_id=oid, level='daily', date=day).update_one(upsert=True, **commands)


class WithMetrics(object):
    metrics = db.DictField()


class Metrics(db.Document):
    object_id = db.DynamicField(required=True)
    date = db.StringField(required=True)
    level = db.StringField(required=True, default='daily', choices=('daily', 'monthly'))
    values = db.DictField()

    meta = {
        'indexes': [
            'object_id',
            'level',
            'date',
            {
                'fields': ('object_id', 'level', '-date'),
                'unique': True,
            }
        ],
        'queryset_class': MetricsQuerySet,
    }

    def __unicode__(self):
        return 'Metrics for object {0} on {1} ({2})'.format(
            self.object_id, self.date, self.level
        )
