# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from werkzeug.datastructures import FileStorage
from flask.ext.security import current_user

from udata import search
from udata.api import api, ModelAPI, ModelListAPI, API
from udata.models import User, FollowUser, Reuse, Dataset

from udata.core.dataset.api_fields import dataset_full_fields
from udata.core.followers.api import FollowAPI
from udata.core.reuse.api_fields import reuse_fields

from .api_fields import (
    apikey_fields,
    me_fields,
    user_fields,
    user_page_fields,
    user_suggestion_fields,
    notifications_fields,
    avatar_fields
)
from .forms import UserProfileForm
from .search import UserSearch

ns = api.namespace('users', 'User related operations')
me = api.namespace('me', 'Connected user related operations')
search_parser = api.search_parser(UserSearch)


@me.route('/', endpoint='me')
class MeAPI(API):
    @api.secure
    @api.doc('get_me')
    @api.marshal_with(me_fields)
    def get(self):
        '''Fetch the current user (me) identity'''
        return current_user._get_current_object()

    @api.secure
    @api.marshal_with(user_fields)
    @api.doc('update_me', responses={400: 'Validation error'})
    def put(self, **kwargs):
        '''Update my profile'''
        user = current_user._get_current_object()
        form = api.validate(UserProfileForm, user)
        return form.save()


avatar_parser = api.parser()
avatar_parser.add_argument('file', type=FileStorage, location='files')
avatar_parser.add_argument('bbox', type=str, location='form')


@me.route('/avatar', endpoint='my_avatar')
@api.doc(parser=avatar_parser)
class AvatarAPI(API):
    @api.secure
    @api.doc('my_avatar')
    @api.marshal_with(avatar_fields)
    def post(self):
        '''Upload a new avatar'''
        args = avatar_parser.parse_args()

        avatar = args['file']
        bbox = ([int(float(c)) for c in args['bbox'].split(',')]
                if 'bbox' in args else None)
        current_user.avatar.save(avatar, bbox=bbox)
        current_user.save()

        return current_user


@me.route('/reuses/', endpoint='my_reuses')
class MyReusesAPI(API):
    @api.secure
    @api.doc('my_reuses')
    @api.marshal_list_with(reuse_fields)
    def get(self):
        '''List all my reuses (including private ones)'''
        return list(Reuse.objects.owned_by(current_user.id))


@me.route('/datasets/', endpoint='my_datasets')
class MyDatasetsAPI(API):
    @api.secure
    @api.doc('my_datasets')
    @api.marshal_list_with(dataset_full_fields)
    def get(self):
        '''List all my datasets (including private ones)'''
        return list(Dataset.objects.owned_by(current_user.id))


@me.route('/apikey', endpoint='my_apikey')
class ApiKeyAPI(API):
    @api.secure
    @api.doc('generate_apikey')
    @api.marshal_with(apikey_fields)
    @api.response(201, 'API Key generated')
    def post(self):
        '''(Re)Generate my API Key'''
        current_user.generate_api_key()
        current_user.save()
        return current_user, 201

    @api.secure
    @api.doc('clear_apikey')
    @api.response(204, 'API Key deleted/cleared')
    def delete(self):
        '''Clear/destroy an apikey'''
        current_user.apikey = None
        current_user.save()
        return '', 204


@ns.route('/', endpoint='users')
@api.doc(get={
    'id': 'list_users',
    'model': user_page_fields,
    'parser': search_parser})
@api.doc(post={'id': 'create_user', 'model': user_fields})
class UserListAPI(ModelListAPI):
    model = User
    fields = user_fields
    form = UserProfileForm
    search_adapter = UserSearch


@ns.route('/<user:user>/', endpoint='user')
@api.doc(model=user_fields, get={'id': 'get_user'})
@api.doc(put={'id': 'update_user', 'body': user_fields})
class UserAPI(ModelAPI):
    model = User
    fields = user_fields
    form = UserProfileForm


@ns.route('/<id>/followers/', endpoint='user_followers')
class FollowUserAPI(FollowAPI):
    model = FollowUser

    @api.secure
    @api.doc(notes="You can't follow yourself.",
             response={403: 'When tring to follow yourself'})
    def post(self, id):
        '''Follow an user given its ID'''
        if id == str(current_user.id):
            api.abort(403, "You can't follow yourself")
        return super(FollowUserAPI, self).post(id)


suggest_parser = api.parser()
suggest_parser.add_argument(
    'q', type=unicode, help='The string to autocomplete/suggest',
    location='args', required=True)
suggest_parser.add_argument(
    'size', type=int, help='The amount of suggestion to fetch',
    location='args', default=10)


@ns.route('/suggest/', endpoint='suggest_users')
class SuggestUsersAPI(API):
    @api.marshal_list_with(user_suggestion_fields)
    @api.doc('suggest_users', parser=suggest_parser)
    def get(self):
        '''Suggest users'''
        args = suggest_parser.parse_args()
        return [
            {
                'id': opt['text'],
                'first_name': opt['payload']['first_name'],
                'last_name': opt['payload']['last_name'],
                'avatar_url': opt['payload']['avatar_url'],
                'slug': opt['payload']['slug'],
                'score': opt['score'],
            }
            for opt in search.suggest(args['q'], 'user_suggest', args['size'])
        ]
