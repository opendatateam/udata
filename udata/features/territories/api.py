# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.api import api, API
from udata.features.territories import check_for_counties, check_for_towns

suggest_parser = api.parser()
suggest_parser.add_argument(
    'q', type=str, help='The string to autocomplete/suggest',
    location='args', required=True)
suggest_parser.add_argument(
    'size', type=int, help='The maximum result size',
    location='args', required=False)


@api.route('/territory/suggest/', endpoint='suggest_territory')
class SuggestTownsTerritoriesAPI(API):
    @api.doc(id='suggest_territory_towns', parser=suggest_parser)
    def get(self):
        args = suggest_parser.parse_args()
        towns = check_for_towns(args['q'].decode('utf-8'))
        counties = check_for_counties(args['q'].decode('utf-8'))
        territories = list(set(counties) | set(towns))
        if args['size']:
            territories = territories[:args['size']]
        return [{
            'id': territory.id,
            'title': territory.name,
            'county': territory.county and territory.county.name or None,
            'region': territory.region and territory.region.name or None,
            'image_url': territory.logo_url(external=True),
            'page': territory.external_url
        } for territory in territories]
