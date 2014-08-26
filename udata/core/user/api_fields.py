# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import url_for

from udata.api import api, fields

from udata.core.organization.api_fields import OrganizationReference

user_fields = api.model('User', {
    'id': fields.String(description='The user identifier', required=True),
    'slug': fields.String(description='The user permalink string', required=True),
    'email': fields.String(description='The user email', required=True),
    'first_name': fields.String(description='The user first name', required=True),
    'last_name': fields.String(description='The user last name', required=True),
    'avatar_url': fields.String(description='The user avatar URL'),
    'website': fields.String(description='The user website'),
    'about': fields.String(description='The user self description'),
    'organizations': fields.List(OrganizationReference, description='The organization the user belongs to'),
})


@api.model(fields={
    'id': fields.String(description='The user identifier', required=True),
    'first_name': fields.String(description='The user first name', required=True),
    'last_name': fields.String(description='The user larst name', required=True),
    'page': fields.String(description='The user profile page URL', required=True),
    'avatar_url': fields.String(description='The user avatar URL'),
})
class UserReference(fields.Raw):
    def format(self, user):
        return {
            'id': str(user.id),
            # 'uri': url_for('api.organization', slug=organization.slug, _external=True),
            'page': url_for('users.show', user=user, _external=True),
            'first_name': user.first_name,
            'last_name': user.last_name,
            'avatar_url': user.avatar_url,
        }
