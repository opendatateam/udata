# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.api import api, API, fields
from udata.search import es

DEFAULT_SIZE = 8

ns = api.namespace('suggest', 'Completion suggester APIs')

parser = api.parser()
parser.add_argument('q', type=str, help='The string to autocomplete/suggest', location='args', required=True)
parser.add_argument('size', type=int, help='The amount of suggestion to fetch', location='args', default=DEFAULT_SIZE)


@ns.route('/tags', endpoint='suggest_tags', doc={'parser': parser})
class SuggestTagsAPI(API):
    def get(self):
        '''Suggest tags'''
        args = parser.parse_args()
        result = es.suggest(index=es.index_name, body={
            'tags': {
                'text': args['q'],
                'completion': {
                    'field': 'tag_suggest',
                    'size': args['size'],
                }
            }
        })
        if 'tags' not in result:
            return []
        return sorted(result['tags'][0]['options'], key=lambda o: len(o['text']))


@ns.route('/formats', endpoint='suggest_formats', doc={'parser': parser})
class SuggestFormatsAPI(API):
    def get(self):
        '''Suggest file formats'''
        args = parser.parse_args()
        result = es.suggest(index=es.index_name, body={
            'formats': {
                'text': args['q'],
                'completion': {
                    'field': 'format_suggest',
                    'size': args['size'],
                }
            }
        })
        if 'formats' not in result:
            return []
        return sorted(result['formats'][0]['options'], key=lambda o: len(o['text']))


@ns.route('/organizations', endpoint='suggest_orgs', doc={'parser': parser})
class SuggestOrgsAPI(API):
    @api.marshal_list_with(api.model('OrganizationSuggestion', {
        'id': fields.String(description='The organization identifier', required=True),
        'name': fields.String(description='The organization name', required=True),
        'slug': fields.String(description='The organization permalink string', required=True),
        'image_url': fields.String(description='The organization logo URL'),
        'score': fields.Float(description='The internal match score', required=True),
    }))
    def get(self):
        '''Suggest organizations'''
        args = parser.parse_args()
        result = es.suggest(index=es.index_name, body={
            'organizations': {
                'text': args['q'],
                'completion': {
                    'field': 'org_suggest',
                    'size': args['size'],
                }
            }
        })
        if 'organizations' not in result:
            return []
        return [
            {
                'id': opt['payload']['id'],
                'name': opt['text'],
                'score': opt['score'],
                'slug': opt['payload']['slug'],
                'image_url': opt['payload']['image_url'],
            }
            for opt in result['organizations'][0]['options']
        ]


@ns.route('/datasets', endpoint='suggest_datasets', doc={'parser': parser})
class SuggestDatasetsAPI(API):
    @api.marshal_list_with(api.model('DatasetSuggestion', {
        'id': fields.String(description='The dataset identifier', required=True),
        'title': fields.String(description='The dataset title', required=True),
        'slug': fields.String(description='The dataset permalink string', required=True),
        'image_url': fields.String(description='The dataset (organization) logo URL'),
        'score': fields.Float(description='The internal match score', required=True),
    }))
    def get(self):
        '''Suggest datasets'''
        args = parser.parse_args()
        result = es.suggest(index=es.index_name, body={
            'datasets': {
                'text': args['q'],
                'completion': {
                    'field': 'dataset_suggest',
                    'size': args['size'],
                }
            }
        })
        if 'datasets' not in result:
            return []
        return [
            {
                'id': opt['payload']['id'],
                'title': opt['text'],
                'score': opt['score'],
                'slug': opt['payload']['slug'],
                'image_url': opt['payload']['image_url'],
            }
            for opt in result['datasets'][0]['options']
        ]


@ns.route('/reuses', endpoint='suggest_reuses', doc={'parser': parser})
class SuggestReusesAPI(API):
    @api.marshal_list_with(api.model('ReuseSuggestion', {
        'id': fields.String(description='The reuse identifier', required=True),
        'title': fields.String(description='The reuse title', required=True),
        'slug': fields.String(description='The reuse permalink string', required=True),
        'image_url': fields.String(description='The reuse thumbnail URL'),
        'score': fields.Float(description='The internal match score', required=True),
    }))
    def get(self):
        '''Suggest reuses'''
        args = parser.parse_args()
        result = es.suggest(index=es.index_name, body={
            'reuses': {
                'text': args['q'],
                'completion': {
                    'field': 'reuse_suggest',
                    'size': args['size'],
                }
            }
        })
        if 'reuses' not in result:
            return []
        return [
            {
                'id': opt['payload']['id'],
                'title': opt['text'],
                'score': opt['score'],
                'slug': opt['payload']['slug'],
                'image_url': opt['payload']['image_url'],
            }
            for opt in result['reuses'][0]['options']
        ]


@ns.route('/users', endpoint='suggest_users', doc={'parser': parser})
class SuggestUsersAPI(API):
    @api.marshal_list_with(api.model('UserSuggestion', {
        'id': fields.String(description='The user identifier', required=True),
        'fullname': fields.String(description='The user fullname', required=True),
        'avatar_url': fields.String(description='The user avatar URL'),
        'slug': fields.String(description='The user permalink string', required=True),
        'score': fields.Float(description='The internal match score', required=True),
    }))
    def get(self):
        '''Suggest users'''
        args = parser.parse_args()
        result = es.suggest(index=es.index_name, body={
            'users': {
                'text': args['q'],
                'completion': {
                    'field': 'user_suggest',
                    'size': args['size'],
                }
            }
        })
        if 'users' not in result:
            return []
        return [
            {
                'id': opt['payload']['id'],
                'fullname': opt['payload']['fullname'],
                'avatar_url': opt['payload']['avatar_url'],
                'slug': opt['payload']['slug'],
                'score': opt['score'],
            }
            for opt in result['users'][0]['options']
        ]


@ns.route('/territories', endpoint='suggest_territories', doc={'parser': parser})
class SuggestTerritoriesAPI(API):
    @api.marshal_list_with(api.model('TerritorySuggestion', {
        'id': fields.String(description='The territory identifier', required=True),
        'name': fields.String(description='The territory name', required=True),
        'code': fields.String(description='The territory main code', required=True),
        'level': fields.String(description='The territory administrative level', required=True),
        'keys': fields.Raw(description='The territory known codes'),
        'score': fields.Float(description='The internal match score', required=True),
    }))
    def get(self):
        '''Suggest territories'''
        args = parser.parse_args()
        result = es.suggest(index=es.index_name, body={
            'territories': {
                'text': args['q'],
                'completion': {
                    'field': 'territory_suggest',
                    'size': args['size'],
                }
            }
        })

        if 'territories' not in result:
            return []

        return [
            {
                'id': opt['payload']['id'],
                'name': opt['payload']['name'],
                'code': opt['payload']['code'],
                'level': opt['payload']['level'],
                'keys': opt['payload']['keys'],
                'score': opt['score'],
            }
            for opt in result['territories'][0]['options']
        ]
