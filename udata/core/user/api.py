# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask.ext.security import current_user

from udata.api import api, ModelAPI, ModelListAPI, API
from udata.models import User, FollowUser, Reuse
from udata.forms import UserProfileForm

from udata.core.followers.api import FollowAPI
from udata.core.reuse.api_fields import reuse_fields

from .api_fields import user_fields, user_page_fields
from .search import UserSearch

ns = api.namespace('users', 'User related operations')
search_parser = api.search_parser(UserSearch)


@api.route('/me/', endpoint='me')
@api.doc(get={'model': user_fields, 'id': 'get_me'})
class MeAPI(ModelAPI):
    model = User
    form = UserProfileForm
    fields = user_fields
    decorators = [api.secure]

    def get_or_404(self, **kwargs):
        if not current_user.is_authenticated():
            api.abort(404)
        return current_user._get_current_object()


@api.route('/me/reuses/', endpoint='my_reuses')
class MyReusesAPI(API):
    @api.marshal_list_with(reuse_fields)
    def get(self):
        '''List all my reuses (including private ones)'''
        if not current_user.is_authenticated():
            api.abort(401)
        return list(Reuse.objects(owner=current_user.id))


@ns.route('/', endpoint='users')
@api.doc(get={'id': 'list_users', 'model': user_page_fields, 'parser': search_parser})
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
    @api.doc(notes="You can't follow yourself.", response={403: 'When tring to follow yourself'})
    def post(self, id):
        '''Follow an user given its ID'''
        if id == str(current_user.id):
            api.abort(403, "You can't follow yourself")
        return super(FollowUserAPI, self).post(id)
