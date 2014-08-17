# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.api import api, API
from udata.search import es

DEFAULT_SIZE = 8

ns = api.namespace('suggest', 'Completion suggester APIs')

parser = api.parser()
parser.add_argument('q', type=str, help='The string to autocomplete/suggest', location='args', required=True)
parser.add_argument('size', type=int, help='The moutn of suggestion to fetch', location='args', default=DEFAULT_SIZE)


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
        return sorted(result['formats'][0]['options'], key=lambda o: len(o['text']))


@ns.route('/organizations', endpoint='suggest_orgs', doc={'parser': parser})
class SuggestOrgsAPI(API):
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
        return [
            {
                'id': opt['payload']['id'],
                'fullname': opt['payload']['fullname'],
                'avatar_url': opt['payload']['avatar_url'],
                'score': opt['score'],
            }
            for opt in result['users'][0]['options']
        ]
