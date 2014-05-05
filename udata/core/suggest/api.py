# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import request

from udata.api import api, API
from udata.search import es

DEFAULT_SIZE = 8


class SuggestTagsAPI(API):
    def get(self):
        q = request.args.get('q', '')
        size = request.args.get('size', DEFAULT_SIZE)
        result = es.suggest(index=es.index_name, body={
            'tags': {
                'text': q,
                'completion': {
                    'field': 'tag_suggest',
                    'size': size
                }
            }
        })
        return result['tags'][0]['options']


class SuggestFormatsAPI(API):
    def get(self):
        q = request.args.get('q', '')
        size = request.args.get('size', DEFAULT_SIZE)
        result = es.suggest(index=es.index_name, body={
            'formats': {
                'text': q,
                'completion': {
                    'field': 'format_suggest',
                    'size': size
                }
            }
        })
        return result['formats'][0]['options']


class SuggestOrgsAPI(API):
    def get(self):
        return []


class SuggestDatasetsAPI(API):
    def get(self):
        q = request.args.get('q', '')
        size = request.args.get('size', DEFAULT_SIZE)
        result = es.suggest(index=es.index_name, body={
            'datasets': {
                'text': q,
                'completion': {
                    'field': 'title_suggest',
                    'size': size
                }
            }
        })
        return [
            {
                'id': opt['payload']['id'],
                'title': opt['text'],
                'score': opt['score'],
            }
            for opt in result['datasets'][0]['options']
        ]


class SuggestUsersAPI(API):
    def get(self):
        q = request.args.get('q', '')
        size = request.args.get('size', DEFAULT_SIZE)
        result = es.suggest(index=es.index_name, body={
            'users': {
                'text': q,
                'completion': {
                    'field': 'user_suggest',
                    'size': size
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


api.add_resource(SuggestTagsAPI, '/suggest/tags', endpoint=b'api.suggest_tags')
api.add_resource(SuggestOrgsAPI, '/suggest/organizations', endpoint=b'api.suggest_orgs')
api.add_resource(SuggestDatasetsAPI, '/suggest/datasets', endpoint=b'api.suggest_datasets')
api.add_resource(SuggestFormatsAPI, '/suggest/formats', endpoint=b'api.suggest_formats')
api.add_resource(SuggestUsersAPI, '/suggest/users', endpoint=b'api.suggest_users')
