from flask import current_app, abort

from flask_restplus import inputs

from udata.api import api, API
from udata import search
from udata.i18n import _
from udata.models import Dataset, TERRITORY_DATASETS
from udata.core.dataset.api_fields import dataset_ref_fields

from .api_fields import (
    level_fields,
    granularity_fields,
    zone_suggestion_fields,
    feature_collection_fields,
)
from .models import GeoZone, GeoLevel, spatial_granularities


GEOM_TYPES = (
    'Point', 'LineString', 'Polygon', 'MultiPoint', 'MultiLineString',
    'MultiPolygon'
)


ns = api.namespace('spatial', 'Spatial references')

suggest_parser = api.parser()
suggest_parser.add_argument(
    'q', type=str, help='The string to autocomplete/suggest',
    location='args', required=True)
suggest_parser.add_argument(
    'size', type=int, help='The amount of suggestion to fetch',
    location='args', default=10)

dataset_parser = api.parser()
dataset_parser.add_argument(
    'dynamic', type=inputs.boolean, help='Append dynamic datasets',
    location='args', required=False)
dataset_parser.add_argument(
    'size', type=int, help='The amount of datasets to fetch',
    location='args', default=25)


def payload_name(payload):
    '''extract payload name and localize it'''
    name = payload['name']
    return _(name)  # Avoid dict quotes in gettext


@ns.route('/zones/suggest/', endpoint='suggest_zones')
class SuggestZonesAPI(API):
    @api.marshal_list_with(zone_suggestion_fields)
    @api.expect(suggest_parser)
    @api.doc('suggest_zones')
    def get(self):
        '''Suggest geospatial zones'''
        args = suggest_parser.parse_args()
        return [
            {
                'id': opt['text'],
                'name': payload_name(opt['payload']),
                'code': opt['payload']['code'],
                'level': opt['payload']['level'],
                'keys': opt['payload']['keys'],
                'score': opt['score'],
            }
            for opt in search.suggest(
                args['q'], 'zone_suggest', args['size'])
        ]


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


@ns.route('/zone/<path:id>/children/', endpoint='zone_children')
class ZoneChildrenAPI(API):
    @api.doc('spatial_zone_children', params={'id': 'A zone identifier'})
    @api.marshal_list_with(feature_collection_fields)
    def get(self, id):
        '''Fetch children of a zone.'''
        zone = GeoZone.objects.get_or_404(id=id)
        if not current_app.config.get('ACTIVATE_TERRITORIES'):
            return abort(501)
        return {
            'type': 'FeatureCollection',
            'features': [z.toGeoJSON() for z in zone.children]
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
        if (args.get('dynamic') and
                current_app.config.get('ACTIVATE_TERRITORIES')):
            DATASETS = TERRITORY_DATASETS[zone.level_code]
            dynamic_dataset_classes = sorted(DATASETS.values(),
                                             key=lambda a: a.order)
            datasets = [
                dynamic_dataset_class(zone)
                for dynamic_dataset_class in dynamic_dataset_classes
            ]
        else:
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
            'name': _(level.name),
            'parents': [p.id for p in level.parents],
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
            ids = GeoZone.objects(parents=zone.id).only('id').distinct('id')
            ids.append(zone.id)
            # Count datasets in zone
            nb_datasets = Dataset.objects(spatial__zones__in=ids).count()
            features.append({
                'id': zone.id,
                'type': 'Feature',
                'geometry': zone.geom,
                'properties': {
                    'name': _(zone.name),
                    'code': zone.code,
                    'level': zone.level,
                    'datasets': nb_datasets
                }
            })

        return {
            'type': 'FeatureCollection',
            'features': features
        }
