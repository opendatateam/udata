# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import url_for
from flask.ext.restful import fields

from udata.api import api, pager


org_fields = api.model('Organization', {
    'id': fields.String,
    'name': fields.String,
    'slug': fields.String,
    'description': fields.String,
    'created_at': fields.ISODateTime,
    'last_modified': fields.ISODateTime,
    'deleted': fields.ISODateTime,
    'metrics': fields.Raw,
    'uri': fields.UrlFor('api.organization', lambda o: {'org': o}),
})

org_page_fields = api.model('OrganizationPage', pager(org_fields))

request_fields = api.model('MembershripRequest', {
    'status': fields.String,
    'comment': fields.String,
})

member_fields = api.model('Member', {
    'user': fields.String,
    'role': fields.String,
})


@api.model('OrganizationReference')
class OrganizationField(fields.Raw):
    def format(self, organization):
        return {
            'id': str(organization.id),
            'uri': url_for('api.organization', org=organization, _external=True),
            'page': url_for('organizations.show', org=organization, _external=True),
        }
