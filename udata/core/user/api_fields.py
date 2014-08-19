# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import url_for

from udata.api import api, fields

from udata.core.organization.api_fields import OrganizationField

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
