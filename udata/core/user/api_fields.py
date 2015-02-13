# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import url_for

from udata.api import api, fields, pager


@api.model(fields={
    'id': fields.String(description='The user identifier', required=True),
    'first_name': fields.String(description='The user first name', required=True),
    'last_name': fields.String(description='The user larst name', required=True),
    'page': fields.String(description='The user profile page URL', required=True),
    'avatar': fields.String(description='The user avatar URL'),
})
class UserReference(fields.Raw):
    def format(self, user):
        return {
            'id': str(user.id),
            # 'uri': url_for('api.organization', slug=organization.slug, _external=True),
            'page': url_for('users.show', user=user, _external=True),
            'first_name': user.first_name,
            'last_name': user.last_name,
            'avatar': user.avatar(100, external=True),
        }


from udata.core.organization.api_fields import OrganizationReference

user_fields = api.model('User', {
    'id': fields.String(description='The user identifier', required=True),
    'slug': fields.String(description='The user permalink string', required=True),
    'first_name': fields.String(description='The user first name', required=True),
    'last_name': fields.String(description='The user last name', required=True),
    'avatar': fields.ImageField(description='The user avatar URL'),
    'website': fields.String(description='The user website'),
    'about': fields.Markdown(description='The user self description'),
    'roles': fields.List(fields.String, description='Site wide user roles'),
    'organizations': fields.List(OrganizationReference, description='The organization the user belongs to'),
    'metrics': fields.Raw(description='Th last user metrics'),
    'since': fields.ISODateTime(attribute='created_at', description='The registeration date', required=True),
})

user_page_fields = api.model('UserPage', pager(user_fields))

user_suggestion_fields = api.model('UserSuggestion', {
    'id': fields.String(description='The user identifier', required=True),
    'fullname': fields.String(description='The user fullname', required=True),
    'avatar_url': fields.String(description='The user avatar URL'),
    'slug': fields.String(description='The user permalink string', required=True),
    'score': fields.Float(description='The internal match score', required=True),
})
