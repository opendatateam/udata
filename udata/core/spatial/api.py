# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask.ext.restplus import fields as base_fields

from udata.api import api, API, fields

from . import LEVELS
from udata import search
from udata.models import SPATIAL_GRANULARITIES, Territory, Dataset


GEOM_TYPES = ('Point', 'LineString', 'Polygon', 'MultiPoint', 'MultiLineString', 'MultiPolygon')


ns = api.namespace('spatial', 'Spatial references')


@api.model(fields={
    'type': fields.String(description='The GeoJSON Type', required=True, enum=GEOM_TYPES),
    'coordinates': fields.List(base_fields.Raw(), description='The geometry as coordinates lists', required=True),
})
class GeoJSON(base_fields.Raw):
    pass

feature_fields = api.model('GeoJSONFeature', {
    'id': fields.String,
    'type': fields.String(required=True, enum=['Feature']),
    'geometry': GeoJSON(required=True),
    'properties': base_fields.Raw,
})

feature_collection_fields = api.model('GeoJSONFeatureCollection', {
    'type': fields.String(required=True, enum=['FeatureCollection']),
    'features': api.as_list(fields.Nested(feature_fields))
})

level_fields = api.model('TerritoryLevel', {
    'id': fields.String(description='The level identifier', required=True),
    'label': fields.String(description='The level name', required=True),
    'position': fields.Integer(description='The position in the level tree (top is zero)', min=0, required=True),
    'parent': fields.String(description='The parent level'),
    'children': fields.List(fields.String, description='The known children levels'),
})

granularity_fields = api.model('SpatialGranularity', {
    'id': fields.String(description='The granularity identifier', required=True),
    'label': fields.String(description='The granularity name', required=True),
})

territory_reference_fields = api.model('TerritoryReference', {
    'id': fields.String(description='The territory identifier', required=True),
    'name': fields.String(description='The territory name', required=True),
    'level': fields.String(description='The territory level identifier', required=True),
    'code': fields.String(description='The territory code (depends on level)', required=True),
})

spatial_coverage_fields = api.model('SpatialCoverage', {
    'geom': GeoJSON(description='A multipolygon for the whole coverage'),
    'territories': api.as_list(fields.Nested(territory_reference_fields, description='The covered teritories')),
    'granularity': fields.String(description='The spatial/territorial granularity', enum=SPATIAL_GRANULARITIES.keys()),
})

territory_suggestion_fields = api.model('TerritorySuggestion', {
    'id': fields.String(description='The territory identifier', required=True),
    'name': fields.String(description='The territory name', required=True),
    'code': fields.String(description='The territory main code', required=True),
    'level': fields.String(description='The territory administrative level', required=True),
    'keys': base_fields.Raw(description='The territory known codes'),
    'score': base_fields.Float(description='The internal match score', required=True),
})


@ns.route('/levels/', endpoint='territory_levels')
class TerritoryLevelsAPI(API):
    @api.marshal_list_with(level_fields)
    def get(self):
        '''List all known levels'''
        return [{
            'id': id,
            'label': level['label'],
            'position': level['position'],
            'parent': level.get('parent'),
            'children': level['children'],
        } for id, level in LEVELS.items()]


@ns.route('/granularities/', endpoint='spatial_granularities')
class SpatialGranularitiesAPI(API):
    @api.marshal_list_with(granularity_fields)
    def get(self):
        '''List all known spatial granularities'''
        return [{
            'id': id,
            'label': label,
        } for id, label in SPATIAL_GRANULARITIES.items()]


@ns.route('/coverage/<string:level>/', endpoint='spatial_coverage')
class SpatialCoverageAPI(API):
    @api.marshal_list_with(feature_collection_fields)
    def get(self, level):
        pipeline = [
            {'$project': {'territory': '$spatial.territories'}},
            {'$unwind': '$territory'},
            {'$match': {'territory.level': level}},
            {'$group': {'_id': '$territory.id', 'count': {'$sum': 1}}}
        ]
        features = []

        for row in Dataset.objects(spatial__territories__level=level).visible().aggregate(*pipeline):
            territory = Territory.objects.get(id=row['_id'])
            features.append({
                'id': str(territory.id),
                'type': 'Feature',
                'geometry': territory.geom,
                'properties': {
                    'name': territory.name,
                    'code': territory.code,
                    'level': territory.level,
                    'datasets': row['count']
                }
            })

        return {
            'type': 'FeatureCollection',
            'features': features
        }



suggest_parser = api.parser()
suggest_parser.add_argument('q', type=unicode, help='The string to autocomplete/suggest', location='args', required=True)
suggest_parser.add_argument('size', type=int, help='The amount of suggestion to fetch', location='args', default=10)


@ns.route('/territories/suggest/', endpoint='suggest_territories')
class SuggestTerritoriesAPI(API):
    @api.marshal_list_with(territory_suggestion_fields)
    @api.doc(id='suggest_territories', parser=suggest_parser)
    def get(self):
        '''Suggest territories'''
        args = suggest_parser.parse_args()
        return [
            {
                'id': opt['payload']['id'],
                'name': opt['payload']['name'],
                'code': opt['payload']['code'],
                'level': opt['payload']['level'],
                'keys': opt['payload']['keys'],
                'score': opt['score'],
            }
            for opt in search.suggest(args['q'], 'territory_suggest', args['size'])
        ]
