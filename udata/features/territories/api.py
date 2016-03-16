# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import url_for
from udata.api import api, API
from udata.features.territories import check_for_territories

suggest_parser = api.parser()
suggest_parser.add_argument(
    'q', type=str, help='The string to autocomplete/suggest',
    location='args', required=True)
suggest_parser.add_argument(
    'size', type=int, help='The maximum result size',
    location='args', required=False)


@api.route('/territory/suggest/', endpoint='suggest_territory')
class SuggestTerritoriesAPI(API):
    @api.doc(id='suggest_territory', parser=suggest_parser)
    def get(self):
        args = suggest_parser.parse_args()
        territories = check_for_territories(args['q'].decode('utf-8'))
        if args['size']:
            territories = territories[:args['size']]
        return [{
            'id': territory.id,
            'title': territory.name,
            'image_url': territory.logo_url(external=True),
            'page': url_for('territories.territory',
                            territory=territory, _external=True)
        } for territory in territories]
