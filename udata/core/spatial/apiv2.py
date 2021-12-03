from mongoengine.queryset.visitor import Q

from udata.api import apiv2, API, fields
from udata.i18n import _
from .models import GeoZone


ns = apiv2.namespace('spatial', 'Spatial references')

DEFAULT_SORTING = '-created_at'


suggest_parser = apiv2.parser()
suggest_parser.add_argument(
    'q', type=str, help='The string to autocomplete/suggest',
    location='args', required=True)
suggest_parser.add_argument(
    'size', type=int, help='The amount of suggestion to fetch',
    location='args', default=10)


zone_suggestion_fields = apiv2.model('TerritorySuggestion', {
    'id': fields.String(description='The territory identifier', required=True),
    'name': fields.String(description='The territory name', required=True),
    'code': fields.String(
        description='The territory main code', required=True),
    'level': fields.String(
        description='The territory administrative level', required=True),
    'keys': fields.Raw(description='The territory known codes')
})


def payload_name(name):
    '''localize name'''
    return _(name)  # Avoid dict quotes in gettext


@ns.route('/zones/suggest/', endpoint='suggest_zones')
class SuggestZonesAPI(API):
    @apiv2.marshal_list_with(zone_suggestion_fields)
    @apiv2.expect(suggest_parser)
    @apiv2.doc('suggest_zones')
    def get(self):
        '''Geospatial zones suggest endpoint using mongoDB contains'''
        args = suggest_parser.parse_args()
        geozones = GeoZone.objects(Q(name__icontains=args['q']) | Q(code__icontains=args['q']))
        return [
            {
                'id': geozone.id,
                'name': payload_name(geozone.name),
                'code': geozone.code,
                'level': geozone.level,
                'keys': geozone.keys
            }
            for geozone in geozones.order_by(DEFAULT_SORTING).limit(args['size']) if geozone.is_current
        ]
