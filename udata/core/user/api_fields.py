# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.api import api, fields, base_reference

from .models import AVATAR_SIZES

BIGGEST_AVATAR_SIZE = AVATAR_SIZES[0]


user_ref_fields = api.inherit('UserReference', base_reference, {
    'first_name': fields.String(
        description='The user first name', readonly=True),
    'last_name': fields.String(
        description='The user larst name', readonly=True),
    'slug': fields.String(
        description='The user permalink string', required=True),
    'page': fields.UrlFor(
        'users.show', lambda u: {'user': u},
        description='The user profile page URL', readonly=True),
    'uri': fields.UrlFor(
        'api.user', lambda o: {'user': o},
        description='The user API URI', required=True),
    'avatar': fields.ImageField(original=True,
        description='The user avatar URL'),
    'avatar_thumbnail': fields.ImageField(attribute='avatar', size=BIGGEST_AVATAR_SIZE,
        description='The user avatar thumbnail URL. This is the square '
        '({0}x{0}) and cropped version.'.format(BIGGEST_AVATAR_SIZE)),
})


from udata.core.organization.api_fields import org_ref_fields  # noqa

user_fields = api.model('User', {
    'id': fields.String(
        description='The user identifier', required=True),
    'slug': fields.String(
        description='The user permalink string', required=True),
    'first_name': fields.String(
        description='The user first name', required=True),
    'last_name': fields.String(
        description='The user last name', required=True),
    'avatar': fields.ImageField(original=True,
        description='The user avatar URL'),
    'avatar_thumbnail': fields.ImageField(attribute='avatar', size=BIGGEST_AVATAR_SIZE,
        description='The user avatar thumbnail URL. This is the square '
        '({0}x{0}) and cropped version.'.format(BIGGEST_AVATAR_SIZE)),
    'website': fields.String(description='The user website'),
    'about': fields.Markdown(description='The user self description'),
    'roles': fields.List(fields.String, description='Site wide user roles'),
    'active': fields.Boolean(),
    'organizations': fields.List(
        fields.Nested(org_ref_fields),
        description='The organization the user belongs to'),
    'since': fields.ISODateTime(
        attribute='created_at',
        description='The registeration date', required=True),
    'page': fields.UrlFor(
        'users.show', lambda u: {'user': u},
        description='The user profile page URL', readonly=True),
    'uri': fields.UrlFor(
        'api.user', lambda o: {'user': o},
        description='The user API URI', required=True),
    'metrics': fields.Raw(
        description='The user metrics', readonly=True),
})

me_fields = api.inherit('Me', user_fields, {
    'email': fields.String(description='The user email', required=True),
    'apikey': fields.String(description='The user API Key', readonly=True),
})

me_metrics_fields = api.model('MyMetrics', {
    'id': fields.String(
        description='The user identifier', required=True),
    'resources_availability': fields.Float(
        description="The user's resources availability percentage",
        readonly=True),
    'datasets_org_count': fields.Integer(
        description="The user's orgs datasets number", readonly=True),
    'followers_org_count': fields.Integer(
        description="The user's orgs followers number", readonly=True),
    'datasets_count': fields.Integer(
        description="The user's datasets number", readonly=True),
    'followers_count': fields.Integer(
        description="The user's followers number", readonly=True),
})

apikey_fields = api.model('ApiKey', {
    'apikey': fields.String(description='The user API Key', readonly=True),
})

user_page_fields = api.model('UserPage', fields.pager(user_fields))

user_suggestion_fields = api.model('UserSuggestion', {
    'id': fields.String(description='The user identifier', readonly=True),
    'first_name': fields.String(description='The user first name',
                                readonly=True),
    'last_name': fields.String(description='The user last name',
                               readonly=True),
    'avatar_url': fields.String(description='The user avatar URL'),
    'slug': fields.String(
        description='The user permalink string', readonly=True),
    'score': fields.Float(
        description='The internal match score', readonly=True),
})


notifications_fields = api.model('Notification', {
    'type': fields.String(description='The notification type', readonly=True),
    'created_on': fields.ISODateTime(
        description='The notification creation datetime', readonly=True),
    'details': fields.Raw(
        description='Key-Value details depending on notification type',
        readonly=True)
})


user_role_fields = api.model('UserRole', {
    'name': fields.String(description='The role name', readonly=True),
})
