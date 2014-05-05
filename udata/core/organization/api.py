# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import url_for
from flask.ext.restful import fields

from udata.api import api, ModelAPI, ModelListAPI
from udata.forms import OrganizationForm
from udata.models import Organization
from udata.search import OrganizationSearch


org_fields = {
    'id': fields.String,
    'name': fields.String,
    'slug': fields.String,
    'description': fields.String,
    'created_at': fields.DateTime,
    'metrics': fields.Raw,
}


class OrganizationField(fields.Raw):
    def format(self, organization):
        return {
            'id': str(organization.id),
            'uri': url_for('api.organization', slug=organization.slug, _external=True),
            'page': url_for('organizations.show', org=organization, _external=True),
        }


class OrganizationListAPI(ModelListAPI):
    model = Organization
    fields = org_fields
    form = OrganizationForm
    search_adapter = OrganizationSearch


class OrganizationAPI(ModelAPI):
    model = Organization
    fields = org_fields
    form = OrganizationForm


api.add_resource(OrganizationListAPI, '/organizations/', endpoint=b'api.organizations')
api.add_resource(OrganizationAPI, '/organizations/<slug>', endpoint=b'api.organization')
