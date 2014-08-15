# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import url_for
from flask.ext.security import current_user

from udata.api import api, ModelAPI, fields
from udata.models import User, FollowUser
from udata.forms import UserProfileForm

from udata.core.organization.api import OrganizationField
from udata.core.followers.api import FollowAPI

ns = api.namespace('users', 'User related operations')

user_fields = api.model('User', {
    'id': fields.String,
    'slug': fields.String,
    'email': fields.String,
    'first_name': fields.String,
    'last_name': fields.String,
    'avatar_url': fields.String,
    'website': fields.String,
    'about': fields.String,
    'organizations': fields.List(OrganizationField),
})


@api.model('UserReference')
class UserField(fields.Raw):
    def format(self, user):
        return {
            'id': str(user.id),
            # 'uri': url_for('api.organization', slug=organization.slug, _external=True),
            'page': url_for('users.show', user=user, _external=True),
            'first_name': user.first_name,
            'last_name': user.last_name,
            'avatar_url': user.avatar_url,
        }


@api.route('/me/', endpoint='me')
class MeAPI(ModelAPI):
    model = User
    form = UserProfileForm
    fields = user_fields
    decorators = [api.secure]

    def get_or_404(self, **kwargs):
        if not current_user.is_authenticated():
            api.abort(404)
        return current_user._get_current_object()


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
