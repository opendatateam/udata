from mongoengine.queryset.visitor import Q

from flask_restx import inputs

from udata.api import api, API
from udata.i18n import _
from udata.models import Dataset
from udata.core.dataset.api_fields import dataset_ref_fields

from .api_fields import (
    level_fields,
    granularity_fields,
    feature_collection_fields,
    zone_suggestion_fields
)
from .models import GeoZone, GeoLevel, spatial_granularities


GEOM_TYPES = (
    'Point', 'LineString', 'Polygon', 'MultiPoint', 'MultiLineString',
    'MultiPolygon'
)

DEFAULT_SORTING = '-created_at'


ns = api.namespace('spatial', 'Spatial references')


suggest_parser = api.parser()
suggest_parser.add_argument(
    'q', type=str, help='The string to autocomplete/suggest',
    location='args', required=True)
suggest_parser.add_argument(
    'size', type=int, help='The amount of suggestion to fetch',
    location='args', default=10)


def payload_name(name):
    '''localize name'''
    return _(name)  # Avoid dict quotes in gettext


@ns.route('/zones/suggest/', endpoint='suggest_zones')
class SuggestZonesAPI(API):
    @api.marshal_list_with(zone_suggestion_fields)
    @api.expect(suggest_parser)
    @api.doc('suggest_zones')
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
                'uri': geozone.uri
            }
            for geozone in geozones.order_by(DEFAULT_SORTING).limit(args['size'])
        ]


dataset_parser = api.parser()
dataset_parser.add_argument(
    'dynamic', type=inputs.boolean, help='Append dynamic datasets',
    location='args', required=False)
dataset_parser.add_argument(
    'size', type=int, help='The amount of datasets to fetch',
    location='args', default=25)


@ns.route('/zones/<pathlist:ids>/', endpoint='zones')
class ZonesAPI(API):
    @api.doc('spatial_zones',
             params={'ids': 'A zone identifiers list (comma separated)'})
    @api.marshal_with(feature_collection_fields)
    def get(self, ids):
        '''Fetch a zone list as GeoJSON'''
        zones = GeoZone.objects.in_bulk(ids)
        zones = [zones[id] for id in ids]
        return {
            'type': 'FeatureCollection',
            'features': [z.toGeoJSON() for z in zones],
        }


@ns.route('/zone/<path:id>/datasets/', endpoint='zone_datasets')
class ZoneDatasetsAPI(API):
    @api.doc('spatial_zone_datasets', params={'id': 'A zone identifier'})
    @api.expect(dataset_parser)
    @api.marshal_with(dataset_ref_fields)
    def get(self, id):
        '''Fetch datasets for a given zone'''
        args = dataset_parser.parse_args()
        zone = GeoZone.objects.get_or_404(id=id)
        datasets = []
        datasets += list(Dataset.objects.visible()
                         .filter(spatial__zones=zone)
                         .limit(args['size']))
        return datasets


@ns.route('/zone/<path:id>/', endpoint='zone')
class ZoneAPI(API):
    @api.doc('spatial_zone', params={'id': 'A zone identifier'})
    def get(self, id):
        '''Fetch a zone'''
        zone = GeoZone.objects.get_or_404(id=id)
        return zone.toGeoJSON()


@ns.route('/levels/', endpoint='spatial_levels')
class SpatialLevelsAPI(API):
    @api.doc('spatial_levels')
    @api.marshal_list_with(level_fields)
    def get(self):
        '''List all known levels'''
        return [{
            'id': level.id,
            'name': _(level.name)
        } for level in GeoLevel.objects]


@ns.route('/granularities/', endpoint='spatial_granularities')
class SpatialGranularitiesAPI(API):
    @api.doc('spatial_granularities')
    @api.marshal_list_with(granularity_fields)
    def get(self):
        '''List all known spatial granularities'''
        return [{
            'id': id,
            'name': name,
        } for id, name in spatial_granularities]


@ns.route('/coverage/<path:level>/', endpoint='spatial_coverage')
class SpatialCoverageAPI(API):
    @api.doc('spatial_coverage')
    @api.marshal_list_with(feature_collection_fields)
    def get(self, level):
        '''List each zone for a given level with their datasets count'''
        level = GeoLevel.objects.get_or_404(id=level)
        features = []

        for zone in GeoZone.objects(level=level.id):
            # fetch nested levels IDs
            ids = []
            ids.append(zone.id)
            # Count datasets in zone
            nb_datasets = Dataset.objects(spatial__zones__in=ids).count()
            features.append({
                'id': zone.id,
                'type': 'Feature',
                'properties': {
                    'name': _(zone.name),
                    'code': zone.code,
                    'uri': zone.uri,
                    'datasets': nb_datasets
                }
            })

        return {
            'type': 'FeatureCollection',
            'features': features
        }
