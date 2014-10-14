# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import url_for

from udata.api import api, fields, pager
from udata.core.organization.api_fields import OrganizationReference
from udata.core.spatial.api import spatial_coverage_fields

from .models import UPDATE_FREQUENCIES, RESOURCE_TYPES

resource_fields = api.model('Resource', {
    'id': fields.String(description='The resource unique ID', required=True),
    'title': fields.String(description='The resource title', required=True),
    'description': fields.String(description='The resource markdown description'),
    'type': fields.String(description='Whether the resource is an uploaded file, a remote file or an API',
        required=True, enum=RESOURCE_TYPES.keys()),
    'format': fields.String(description='The resource format', required=True),
    'url': fields.String(description='The resource URL', required=True),
    'checksum': fields.String(description='A checksum to validate file validity'),
    'created_at': fields.ISODateTime(description='The resource creation date', required=True),
    'last_modified': fields.ISODateTime(attribute='modified',
        description='The resource last modification date', required=True),
})

temporal_coverage_fields = api.model('TemporalCoverage', {
    'start': fields.ISODateTime(description='The temporal coverage start date', required=True),
    'end': fields.ISODateTime(description='The temporal coverage end date', required=True),
})

dataset_fields = api.model('Dataset', {
    'id': fields.String(description='The dataset identifier', required=True),
    'title': fields.String(description='The dataset title', required=True),
    'slug': fields.String(description='The dataset permalink string', required=True),
    'description': fields.String(description='The dataset description in markdown', required=True),
    'created_at': fields.ISODateTime(description='The dataset creation date', required=True),
    'last_modified': fields.ISODateTime(description='The dataset last modification date', required=True),
    'deleted': fields.ISODateTime(description='The deletion date if deleted'),
    'featured': fields.Boolean(description='Is the dataset featured'),
    'tags': fields.List(fields.String),
    'resources': api.as_list(fields.Nested(resource_fields, description='The dataset resources')),
    'community_resources': api.as_list(fields.Nested(resource_fields,
        description='The dataset community submitted resources')),
    'frequency': fields.String(description='The update frequency', required=True, enum=UPDATE_FREQUENCIES.keys()),
    'extras': fields.Raw(description='Extras attributes as key-value pairs'),
    'metrics': fields.Raw(description='The dataset metrics'),
    'organization': OrganizationReference(description='The producer organization'),
    'supplier': OrganizationReference(description='The supplyer organization (if different from the producer)'),
    'temporal_coverage': fields.Nested(temporal_coverage_fields, allow_null=True,
        description='The temporal coverage'),
    'spatial': fields.Nested(spatial_coverage_fields, allow_null=True, description='The spatial coverage'),
    'license': fields.String(attribute='license.id', description='The dataset license'),

    'uri': fields.UrlFor('api.dataset', lambda o: {'dataset': o},
        description='The dataset API URI', required=True),
    'page': fields.UrlFor('datasets.show', lambda o: {'dataset': o},
        description='The dataset page URL', required=True),
})

dataset_page_fields = api.model('DatasetPage', pager(dataset_fields))


@api.model(fields={
    'id': fields.String(description='The dataset unique identifier', required=True),
    'title': fields.String(description='The dataset title', required=True),
    'uri': fields.String(description='The API URI for this dataset', required=True),
    'page': fields.String(description='The web page URL for this dataset', required=True),
})
class DatasetReference(fields.Raw):
    def format(self, dataset):
        return {
            'id': str(dataset.id),
            'title': dataset.title,
            'uri': url_for('api.dataset', dataset=dataset, _external=True),
            'page': url_for('datasets.show', dataset=dataset, _external=True),
        }
