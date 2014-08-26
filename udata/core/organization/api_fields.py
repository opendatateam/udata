# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import url_for

from udata.api import api, pager, fields

from .models import ORG_ROLES, MEMBERSHIP_STATUS


org_fields = api.model('Organization', {
    'id': fields.String(description='The organization identifier', required=True),
    'name': fields.String(description='The organization name', required=True),
    'slug': fields.String(description='The organization string used as permalink', required=True),
    'description': fields.String(description='The organization description in Markdown', required=True),
    'created_at': fields.ISODateTime(description='The organization creation date', required=True),
    'last_modified': fields.ISODateTime(description='The organization last modification date', required=True),
    'deleted': fields.ISODateTime(description='The organization deletion date if deleted'),
    'metrics': fields.Raw(description='The organization metrics'),
    'uri': fields.UrlFor('api.organization', lambda o: {'org': o},
        description='The organization API URI', required=True),
    'page': fields.UrlFor('organizations.show', lambda o: {'org': o},
        description='The organization page URL', required=True),
})

org_page_fields = api.model('OrganizationPage', pager(org_fields))

request_fields = api.model('MembershipRequest', {
    'status': fields.String(description='The current request status', required=True,
        enum=MEMBERSHIP_STATUS.keys()),
    'comment': fields.String(description='A request comment from the user', required=True),
})

member_fields = api.model('Member', {
    'user': fields.String,
    'role': fields.String(description='The member role in the organization', required=True,
        enum=ORG_ROLES.keys())
})


@api.model(fields={
    'id': fields.String(description='The organization identifier', required=True),
    'name': fields.String(description='The organization name', required=True),
    'uri': fields.String(description='The organization API URI', required=True),
    'page': fields.String(description='The organization web page URL', required=True),
    'image_url': fields.String(description='The organization logo URL'),
})
class OrganizationReference(fields.Raw):
    def format(self, organization):
        return {
            'id': str(organization.id),
            'uri': url_for('api.organization', org=organization, _external=True),
            'page': url_for('organizations.show', org=organization, _external=True),
            'image_url': organization.image_url,
            'name': organization.name,
        }
