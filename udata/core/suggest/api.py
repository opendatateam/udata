# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import request

from udata.api import api, API
from udata.search import es

DEFAULT_SIZE = 8

ns = api.namespace('suggest', 'Completion suggester APIs')


@ns.resource('/tags', endpoint='suggest_tags')
class SuggestTagsAPI(API):
    def get(self):
        '''Suggest tags'''
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
        return sorted(result['tags'][0]['options'], key=lambda o: len(o['text']))


@ns.resource('/formats', endpoint='suggest_formats')
class SuggestFormatsAPI(API):
    def get(self):
        '''Suggest file formats'''
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
        return sorted(result['formats'][0]['options'], key=lambda o: len(o['text']))


@ns.resource('/organizations', endpoint='suggest_orgs')
class SuggestOrgsAPI(API):
    def get(self):
        '''Suggest organizations'''
        q = request.args.get('q', '')
        size = request.args.get('size', DEFAULT_SIZE)
        result = es.suggest(index=es.index_name, body={
            'organizations': {
                'text': q,
                'completion': {
                    'field': 'org_suggest',
                    'size': size
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


@ns.resource('/datasets', endpoint='suggest_datasets')
class SuggestDatasetsAPI(API):
    def get(self):
        '''Suggest datasets'''
        q = request.args.get('q', '')
        size = request.args.get('size', DEFAULT_SIZE)
        result = es.suggest(index=es.index_name, body={
            'datasets': {
                'text': q,
                'completion': {
                    'field': 'dataset_suggest',
                    'size': size
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


@ns.resource('/reuses', endpoint='suggest_reuses')
class SuggestReusesAPI(API):
    def get(self):
        '''Suggest reuses'''
        q = request.args.get('q', '')
        size = request.args.get('size', DEFAULT_SIZE)
        result = es.suggest(index=es.index_name, body={
            'reuses': {
                'text': q,
                'completion': {
                    'field': 'reuse_suggest',
                    'size': size
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


@ns.resource('/users', endpoint='suggest_users')
class SuggestUsersAPI(API):
    def get(self):
        '''Suggest users'''
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
