# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import url_for

from udata.api import api, fields, pager
from udata.core.organization.api_fields import OrganizationField

resource_fields = api.model('Resource', {
    'id': fields.String,
    'title': fields.String,
    'description': fields.String,
    'url': fields.String,
    'checksum': fields.String,
    'created_at': fields.ISODateTime,
    'last_modified': fields.ISODateTime(attribute='modified'),
})

temporal_coverage_fields = api.model('TemporalCoverage', {
    'start': fields.ISODateTime,
    'end': fields.ISODateTime,
})

dataset_fields = api.model('Dataset', {
    'id': fields.String,
    'title': fields.String,
    'slug': fields.String,
    'description': fields.String,
    'created_at': fields.ISODateTime,
    'last_modified': fields.ISODateTime,
    'deleted': fields.ISODateTime,
    'featured': fields.Boolean,
    'tags': fields.List(fields.String),
    'resources': fields.Nested(resource_fields),
    'community_resources': fields.Nested(resource_fields),
    'frequency': fields.String,
    'extras': fields.Raw,
    'metrics': fields.Raw,
    'organization': OrganizationField,
    'supplier': OrganizationField,
    'temporal_coverage': fields.Nested(temporal_coverage_fields, allow_null=True),
    'license': fields.String(attribute='license.id'),

    'uri': fields.UrlFor('api.dataset', lambda o: {'dataset': o}),
    'page': fields.UrlFor('datasets.show', lambda o: {'dataset': o}),
})

dataset_page_fields = api.model('DatasetPage', pager(dataset_fields))


@api.model('DatasetReference')
class DatasetField(fields.Raw):
    def format(self, dataset):
        return {
            'id': str(dataset.id),
            'uri': url_for('api.dataset', dataset=dataset, _external=True),
            'page': url_for('datasets.show', dataset=dataset, _external=True),
        }
