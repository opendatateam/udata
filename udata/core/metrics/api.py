# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from bson import ObjectId

from flask.ext.restful import fields

from udata.api import api, API, marshal
from udata.models import Metrics

metrics_fields = {
    'object_id': fields.String,
    'date': fields.String,
    'level': fields.String,
    'values': fields.Raw,
}


def parse_period(value):
    if '+' in value:
        start, end = value.split('+')
        return start, end
    else:
        return value


class MetricsAPI(API):
    def get(self, id, period=None, names=None):
        try:
            object_id = ObjectId(id)
        except:
            object_id = id
        queryset = Metrics.objects(object_id=object_id).order_by('-date')
        if period:
            period = parse_period(period)
            if isinstance(period, basestring):
                result = queryset(date=period).first_or_404()
            else:
                result = list(queryset(date__gte=period[0], date__lte=period[1]))
        else:
            result = queryset.first_or_404()
        return marshal(result, metrics_fields)


api.add_resource(MetricsAPI, '/metrics/<id>/', endpoint=b'api.metrics')
api.add_resource(MetricsAPI, '/metrics/<id>/<period>/', endpoint=b'api.metrics_period')
api.add_resource(MetricsAPI, '/metrics/<id>/<period>/<names>/', endpoint=b'api.metrics_by_name')
