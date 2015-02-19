# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.api import api, fields, pager


user_ref_fields = api.model('UserReference', {
    'id': fields.String(description='The user identifier', readonly=True),
    'first_name': fields.String(description='The user first name', readonly=True),
    'last_name': fields.String(description='The user larst name', readonly=True),
    'page': fields.UrlFor('users.show', lambda u: {'user': u},
        description='The user profile page URL', readonly=True),
    'avatar': fields.ImageField(size=100, description='The user avatar URL'),
})


from udata.core.organization.api_fields import org_ref_fields

user_fields = api.model('User', {
    'id': fields.String(description='The user identifier', required=True),
    'slug': fields.String(description='The user permalink string', required=True),
    'first_name': fields.String(description='The user first name', required=True),
    'last_name': fields.String(description='The user last name', required=True),
    'avatar': fields.ImageField(description='The user avatar URL'),
    'website': fields.String(description='The user website'),
    'about': fields.Markdown(description='The user self description'),
    'roles': fields.List(fields.String, description='Site wide user roles'),
    'organizations': fields.List(fields.Nested(org_ref_fields),
        description='The organization the user belongs to'),
    'metrics': fields.Raw(description='Th last user metrics'),
    'since': fields.ISODateTime(attribute='created_at',
        description='The registeration date', required=True),
})

user_page_fields = api.model('UserPage', pager(user_fields))

user_suggestion_fields = api.model('UserSuggestion', {
    'id': fields.String(description='The user identifier', required=True),
    'fullname': fields.String(description='The user fullname', required=True),
    'avatar_url': fields.String(description='The user avatar URL'),
    'slug': fields.String(description='The user permalink string', required=True),
    'score': fields.Float(description='The internal match score', required=True),
})
