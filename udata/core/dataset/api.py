# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import url_for

from udata.api import api, ModelAPI, ModelListAPI, SingleObjectAPI, API, marshal, fields
from udata.core.issues.api import IssuesAPI
from udata.core.organization.api import OrganizationField
from udata.utils import get_by

from .models import Dataset, Resource, DatasetIssue
from .forms import DatasetForm, ResourceForm, DatasetFullForm
from .search import DatasetSearch

ns = api.namespace('datasets', 'Dataset related operations')

resource_fields = {
    'id': fields.String,
    'title': fields.String,
    'description': fields.String,
    'url': fields.String,
    'checksum': fields.String,
    'created_at': fields.ISODateTime,
    'last_modified': fields.ISODateTime(attribute='modified'),
}

temporal_coverage_fields = {
    'start': fields.ISODateTime,
    'end': fields.ISODateTime,
}

dataset_fields = {
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
}

common_doc = {
    'params': {'dataset': {'description': 'The dataset ID or slug'}}
}


class DatasetField(fields.Raw):
    def format(self, dataset):
        return {
            'id': str(dataset.id),
            'uri': url_for('api.dataset', dataset=dataset, _external=True),
            'page': url_for('datasets.show', dataset=dataset, _external=True),
        }


@ns.route('/', endpoint='datasets')
class DatasetListAPI(ModelListAPI):
    model = Dataset
    form = DatasetFullForm
    fields = dataset_fields
    search_adapter = DatasetSearch


@ns.route('/<dataset:dataset>/', endpoint='dataset', doc=common_doc)
class DatasetAPI(ModelAPI):
    model = Dataset
    form = DatasetForm
    fields = dataset_fields


@ns.route('/<dataset:dataset>/featured/', endpoint='dataset_featured', doc=common_doc)
class DatasetFeaturedAPI(SingleObjectAPI, API):
    model = Dataset

    @api.secure
    def post(self, dataset):
        '''Mark the dataset as featured'''
        dataset.featured = True
        dataset.save()
        return marshal(dataset, dataset_fields)

    @api.secure
    def delete(self, dataset):
        '''Unmark the dataset as featured'''
        dataset.featured = False
        dataset.save()
        return marshal(dataset, dataset_fields)


@ns.route('/<dataset:dataset>/resources/', endpoint='resources', doc=common_doc)
class ResourcesAPI(API):
    @api.secure
    def post(self, dataset):
        '''Create a new resource for a given dataset'''
        form = api.validate(ResourceForm)
        resource = Resource()
        form.populate_obj(resource)
        dataset.resources.append(resource)
        dataset.save()
        return marshal(resource, resource_fields), 201


@ns.route('/<dataset:dataset>/resources/<uuid:rid>/', endpoint='resource', doc=common_doc)
@api.doc(params={'rid': {'description': 'The resource unique identifier'}})
class ResourceAPI(API):
    def get_resource_or_404(self, dataset, id):
        resource = get_by(dataset.resources, 'id', id)
        if not resource:
            api.abort(404, 'Ressource does not exists')
        return resource

    @api.secure
    def put(self, dataset, rid):
        '''Update a given resource on a given dataset'''
        resource = self.get_resource_or_404(dataset, rid)
        form = api.validate(ResourceForm, resource)
        form.populate_obj(resource)
        dataset.save()
        return marshal(resource, resource_fields)

    @api.secure
    def delete(self, dataset, rid):
        '''Delete a given resource on a given dataset'''
        resource = self.get_resource_or_404(dataset, rid)
        dataset.resources.remove(resource)
        dataset.save()
        return '', 204


@ns.route('/<id>/issues/', endpoint='dataset_issues')
@api.doc(params={'id': {'description': 'The dataset ID'}})
class DatasetIssuesAPI(IssuesAPI):
    model = DatasetIssue
