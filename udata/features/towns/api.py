# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import url_for
from udata.api import api, API
from udata.features.towns import check_for_town

suggest_parser = api.parser()
suggest_parser.add_argument(
    'q', type=str, help='The string to autocomplete/suggest',
    location='args', required=True)


@api.route('/town/suggest/', endpoint='suggest_town')
class SuggestTerritoriesAPI(API):
    @api.doc(id='suggest_town', parser=suggest_parser)
    def get(self):
        args = suggest_parser.parse_args()
        town = check_for_town(args['q'].decode('utf-8'))
        if town:
            return [
                {
                    'id': town.id,
                    'title': town.name,
                    'image_url': town.logo_url(external=True),
                    'page': url_for('towns.town',
                                    town=town, _external=True)
                }
            ]
        else:
            return []
