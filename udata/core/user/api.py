# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import abort, url_for
from flask.ext.security import current_user

from udata.api import api, ModelAPI, SingleObjectAPI, API, marshal, fields
from udata.models import Dataset, Reuse, Organization, User
from udata.forms import UserProfileForm


user_fields = {
    'id': fields.String,
    'slug': fields.String,
    'email': fields.String,
    'first_name': fields.String,
    'last_name': fields.String,
    'avatar_url': fields.String,
    'website': fields.String,
    'about': fields.String,
}


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


class MeAPI(ModelAPI):
    model = User
    form = UserProfileForm
    fields = user_fields


api.add_resource(MeAPI, '/me/', endpoint=b'api.me')
