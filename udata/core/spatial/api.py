# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.api import api, API, fields

from . import LEVELS
from .models import SPATIAL_GRANULARITIES


level_fields = api.model('TerritoryLevel', {
    'id': fields.String(description='The level identifier', required=True),
    'label': fields.String(description='The level name', required=True),
    'position': fields.Integer(description='The position in the level tree (top is zero)', min=0, required=True),
    'parent': fields.String(description='The parent level'),
    'children': fields.List(fields.String, description='The known children levels'),
})

granularity_fields = api.model('SptialGranularity', {
    'id': fields.String(description='The granularity identifier', required=True),
    'label': fields.String(description='The granularity name', required=True),
})


@api.route('/references/spatial/levels/', endpoint='territory_levels')
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


@api.route('/references/spatial/granularities/', endpoint='spatial_granularities')
class SpatialGranularitiesAPI(API):
    @api.marshal_list_with(granularity_fields)
    def get(self):
        '''List all known spatial granularities'''
        return [{
            'id': id,
            'label': label,
        } for id, label in SPATIAL_GRANULARITIES.items()]
