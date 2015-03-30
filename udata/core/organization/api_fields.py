# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.api import api, pager, fields

from .models import ORG_ROLES, MEMBERSHIP_STATUS


org_ref_fields = api.inherit('OrganizationReference', fields.base_reference, {
    'name': fields.String(description='The organization name', readonly=True),
    'uri': fields.UrlFor('api.organization', lambda o: {'org': o},
        description='The organization API URI', readonly=True),
    'page': fields.UrlFor('organizations.show', lambda o: {'org': o},
        description='The organization web page URL', readonly=True),
    'logo': fields.ImageField(size=100, description='The organization logo URL'),
})


from udata.core.user.api_fields import user_ref_fields

request_fields = api.model('MembershipRequest', {
    'id': fields.String(readonly=True),
    'user': fields.Nested(user_ref_fields),
    'created': fields.ISODateTime(description='The request creation date', readonly=True),
    'status': fields.String(description='The current request status', required=True,
        enum=MEMBERSHIP_STATUS.keys()),
    'comment': fields.String(description='A request comment from the user', required=True),
})

member_fields = api.model('Member', {
    'user': fields.Nested(user_ref_fields),
    'role': fields.String(description='The member role in the organization', required=True,
        enum=ORG_ROLES.keys())
})


org_fields = api.model('Organization', {
    'id': fields.String(description='The organization identifier', required=True),
    'name': fields.String(description='The organization name', required=True),
    'acronym': fields.String(description='The organization acronym'),
    'url': fields.String(description='The organization website URL'),
    'slug': fields.String(description='The organization string used as permalink', required=True),
    'description': fields.Markdown(description='The organization description in Markdown', required=True),
    'created_at': fields.ISODateTime(description='The organization creation date', readonly=True),
    'last_modified': fields.ISODateTime(description='The organization last modification date', readonly=True),
    'deleted': fields.ISODateTime(description='The organization deletion date if deleted', readonly=True),
    'metrics': fields.Raw(description='The organization metrics', readonly=True),
    'uri': fields.UrlFor('api.organization', lambda o: {'org': o},
        description='The organization API URI', readonly=True),
    'page': fields.UrlFor('organizations.show', lambda o: {'org': o},
        description='The organization page URL', readonly=True),
    'logo': fields.ImageField(description='The organization logo URLs'),
    'members': api.as_list(fields.Nested(member_fields, description='The organization members')),
})

org_page_fields = api.model('OrganizationPage', pager(org_fields))

org_suggestion_fields = api.model('OrganizationSuggestion', {
    'id': fields.String(description='The organization identifier', readonly=True),
    'name': fields.String(description='The organization name', readonly=True),
    'slug': fields.String(description='The organization permalink string', readonly=True),
    'image_url': fields.String(description='The organization logo URL', readonly=True),
    'score': fields.Float(description='The internal match score', readonly=True),
})

logo_fields = api.model('UploadedLogo', {
    'success': fields.Boolean(description='Whether the upload succeeded or not.', readonly=True, default=True),
    'logo': fields.ImageField(),
    # 'error': fields.String(description='An error message if success is false', readonly=True),
})
