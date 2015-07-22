# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.api import api, fields


GEOM_TYPES = (
    'Point', 'LineString', 'Polygon', 'MultiPoint', 'MultiLineString',
    'MultiPolygon'
)


geojson = api.model('GeoJSON', {
    'type': fields.String(
        description='The GeoJSON Type', required=True, enum=GEOM_TYPES),
    'coordinates': fields.List(
        fields.Raw(), description='The geometry as coordinates lists',
        required=True),
})

feature_fields = api.model('GeoJSONFeature', {
    'id': fields.String,
    'type': fields.String(required=True, enum=['Feature']),
    'geometry': fields.Nested(geojson, required=True),
    'properties': fields.Raw,
})

feature_collection_fields = api.model('GeoJSONFeatureCollection', {
    'type': fields.String(required=True, enum=['FeatureCollection']),
    'features': fields.List(fields.Nested(feature_fields), required=True)
})

level_fields = api.model('GeoLevel', {
    'id': fields.String(description='The level identifier', required=True),
    'name': fields.String(description='The level name', required=True),
    'parents': fields.List(fields.String, description='The parent levels'),
})

zone_fields = api.model('GeoZone', {
    'id': fields.String(description='The zone identifier', required=True),
    'name': fields.String(description='The zone name', required=True),
    'code': fields.String(
        description='The zone unique code in the level', required=True),
    'level': fields.String(description='The zone level', required=True),
    'parents': fields.List(
        fields.String, description='Every known parent zones'),
    'keys': fields.Raw(
        description='Some arbitry key-value identifying the zone'),
    'population': fields.Integer(
        description='An estimated/approximative population'),
    'area': fields.Integer(description='An estimated/approximative area'),
    'geom': fields.Nested(
        geojson, description='A multipolygon for the whole coverage'),
})

granularity_fields = api.model('GeoGranularity', {
    'id': fields.String(
        description='The granularity identifier', required=True),
    'name': fields.String(description='The granularity name', required=True),
})


spatial_coverage_fields = api.model('SpatialCoverage', {
    'geom': fields.Nested(
        geojson, allow_null=True,
        description='A multipolygon for the whole coverage'),
    'zones': fields.List(
        fields.String, description='The covered zones identifiers'),
    'granularity': fields.String(
        description='The spatial/territorial granularity'),
})

zone_suggestion_fields = api.model('TerritorySuggestion', {
    'id': fields.String(description='The territory identifier', required=True),
    'name': fields.String(description='The territory name', required=True),
    'code': fields.String(
        description='The territory main code', required=True),
    'level': fields.String(
        description='The territory administrative level', required=True),
    'keys': fields.Raw(description='The territory known codes'),
    'score': fields.Float(
        description='The internal match score', required=True),
})
