# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from bson import ObjectId
from datetime import date

from udata.api import api, API, marshal, fields
from udata.models import Metrics


metrics_fields = api.model('Metric', {
    'object_id': fields.String(description='The object identifier which metrics belongs to', required=True),
    'date': fields.String(description='The metrics sampling date', required=True),
    'level': fields.String(description='The metrics granularity level', required=True, enum=['daily', 'monthly']),
    'values': fields.Raw(description='The metrics as key-value pairs', required=True),
})

isodate = lambda v: date(*(int(p) for p in v.split('-'))).isoformat()

parser = api.parser()
parser.add_argument('start', type=isodate, help='Start of the period to fetch', location='args')
parser.add_argument('end', type=isodate, help='End of the period to fetch', location='args')
parser.add_argument('day', type=isodate, help='Specific day date to fetch', location='args')


@api.route('/metrics/<id>', endpoint='metrics')
class MetricsAPI(API):
    @api.doc(model=[metrics_fields], parser=parser)
    @api.doc(params={'id': 'The object ID to fetch metric for'})
    @api.doc(notes='If day is set, start and end will be ignored')
    def get(self, id):
        '''Fetch metrics for an object given its ID'''
        try:
            object_id = ObjectId(id)
        except:
            object_id = id
        queryset = Metrics.objects(object_id=object_id).order_by('-date')
        args = parser.parse_args()
        if args.get('day'):
            result = [queryset(date=args['day']).first_or_404()]
        elif args.get('start'):
            end = args.get('end', date.today().isoformat())
            result = list(queryset(date__gte=args['start'], date__lte=end))
        else:
            result = [queryset.first_or_404()]
        return marshal(result, metrics_fields)
