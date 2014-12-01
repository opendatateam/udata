# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask.ext.security import current_user

from udata.api import api, ModelAPI, API
from udata.models import User, FollowUser, Reuse
from udata.forms import UserProfileForm

from udata.core.followers.api import FollowAPI
from udata.core.reuse.api_fields import reuse_fields

from .api_fields import user_fields

ns = api.namespace('users', 'User related operations')


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


@ns.route('/<id>/follow/', endpoint='follow_user')
class FollowUserAPI(FollowAPI):
    model = FollowUser

    @api.secure
    @api.doc(notes="You can't follow yourself.", response={403: 'When tring to follow yourself'})
    def post(self, id):
        '''Follow an user given its ID'''
        if id == str(current_user.id):
            api.abort(403, "You can't follow yourself")
        return super(FollowUserAPI, self).post(id)
