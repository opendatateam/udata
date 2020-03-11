from bson import ObjectId
from datetime import date

from flask_restplus.inputs import boolean

from udata.api import api, API, fields

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
        pass
