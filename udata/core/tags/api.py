# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata import search
from udata.api import api, API

DEFAULT_SIZE = 8

ns = api.namespace('tags', 'Tags related operations')

parser = api.parser()
parser.add_argument(
    'q', type=str, help='The string to autocomplete/suggest',
    location='args', required=True)
parser.add_argument(
    'size', type=int, help='The amount of suggestion to fetch',
    location='args', default=DEFAULT_SIZE)


@ns.route('/suggest/', endpoint='suggest_tags')
class SuggestTagsAPI(API):
    @api.doc(id='suggest_tags', parser=parser)
    def get(self):
        '''Suggest tags'''
        args = parser.parse_args()
        result = search.suggest(args['q'], 'tag_suggest', args['size'])
        return sorted(result, key=lambda o: len(o['text']))
