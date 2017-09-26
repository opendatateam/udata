# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from bson import ObjectId
from datetime import date

from flask_restplus.inputs import boolean

from udata.api import api, API, fields
from udata.models import Metrics

from udata.core.site.models import current_site


metrics_fields = api.model('Metric', {
    'object_id': fields.String(
        description='The object identifier which metrics belongs to',
        required=True),
    'date': fields.String(
        description='The metrics sampling date', required=True),
    'level': fields.String(
        description='The metrics granularity level', required=True,
        enum=['daily', 'monthly']),
    'values': fields.Raw(
        description='The metrics as key-value pairs', required=True),
})


def isodate(value):
    return date(*(int(p) for p in value.split('-'))).isoformat()


parser = api.parser()
parser.add_argument(
    'start', type=isodate, help='Start of the period to fetch',
    location='args')
parser.add_argument(
    'end', type=isodate, help='End of the period to fetch', location='args')
parser.add_argument(
    'cumulative', type=boolean, help='Either cumulative metrics or not',
    default=True, location='args')
parser.add_argument(
    'day', type=isodate, help='Specific day date to fetch', location='args')


@api.route('/metrics/<id>', endpoint='metrics')
class MetricsAPI(API):
    @api.doc('metrics_for')
    @api.marshal_list_with(metrics_fields)
    @api.expect(parser)
    @api.param('id', 'The object ID to fetch metric for')
    @api.doc(description='If day is set, start and end will be ignored')
    def get(self, id):
        '''Fetch metrics for an object given its ID'''
        if id == 'site':
            object_id = current_site.id
        else:
            try:
                object_id = ObjectId(id)
            except:
                object_id = id
        queryset = Metrics.objects(object_id=object_id).order_by('-date')
        args = parser.parse_args()
        if args.get('day'):
            metrics = [queryset(date=args['day']).first_or_404()]
        elif args.get('start'):
            end = args.get('end', date.today().isoformat())
            metrics = list(queryset(date__gte=args['start'], date__lte=end))
        else:
            metrics = [queryset.first_or_404()]
        if not args.get('cumulative') and metrics:
            # Turn cumulative data into daily counts based on the first
            # result. Might return negative values if there is a drop.
            reference_values = metrics[-1].values.copy()
            for metric in reversed(metrics):
                current_values = metric.values.copy()
                metric.values = {
                    name: count - reference_values[name]
                    for name, count in current_values.iteritems()
                    if name in reference_values
                }
                reference_values = current_values
        return metrics
