# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from uuid import UUID

from flask import request, abort, url_for

from udata.api import api, ModelAPI, ModelListAPI, SingleObjectAPI, API, marshal, fields
from udata.core.issues.api import IssuesAPI
from udata.core.organization.api import OrganizationField
from udata.utils import get_by

from .models import Dataset, Resource, DatasetIssue
from .forms import DatasetForm, ResourceForm
from .search import DatasetSearch

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
    'featured': fields.Boolean,
    'tags': fields.List(fields.String),
    'resources': fields.Nested(resource_fields),
    'community_resources': fields.Nested(resource_fields),
    'frequency': fields.String,
    'extras': fields.Raw,
    'metrics': fields.Raw,
    'organization': OrganizationField,
    'temporal_coverage': fields.Nested(temporal_coverage_fields, allow_null=True),

    'uri': fields.UrlFor('api.dataset', lambda o: {'slug': o.slug}),
}


class DatasetField(fields.Raw):
    def format(self, dataset):
        return {
            'id': str(dataset.id),
            'uri': url_for('api.dataset', slug=dataset.slug, _external=True),
            'page': url_for('datasets.show', dataset=dataset, _external=True),
        }


class DatasetListAPI(ModelListAPI):
    model = Dataset
    form = DatasetForm
    fields = dataset_fields
    search_adapter = DatasetSearch


class DatasetAPI(ModelAPI):
    model = Dataset
    form = DatasetForm
    fields = dataset_fields


class DatasetFeaturedAPI(SingleObjectAPI, API):
    model = Dataset

    @api.secure
    def post(self, slug):
        dataset = self.get_or_404(slug=slug)
        dataset.featured = True
        dataset.save()
        return marshal(dataset, dataset_fields)

    @api.secure
    def delete(self, slug):
        dataset = self.get_or_404(slug=slug)
        dataset.featured = False
        dataset.save()
        return marshal(dataset, dataset_fields)


class ResourcesAPI(API):
    @api.secure
    def post(self, slug):
        dataset = Dataset.objects.get_or_404(slug=slug)
        form = api.validate(ResourceForm)
        resource = Resource()
        form.populate_obj(resource)
        dataset.resources.append(resource)
        dataset.save()
        return marshal(resource, resource_fields), 201


class ResourceAPI(API):
    @api.secure
    def put(self, slug, rid):
        dataset = Dataset.objects.get_or_404(slug=slug)
        resource = get_by(dataset.resources, 'id', UUID(rid))
        if not resource:
            abort(404)
        form = api.validate(ResourceForm, resource)
        form.populate_obj(resource)
        dataset.save()
        return marshal(resource, resource_fields)

    @api.secure
    def delete(self, slug, rid):
        dataset = Dataset.objects.get_or_404(slug=slug)
        resource = get_by(dataset.resources, 'id', UUID(rid))
        if not resource:
            abort(404)
        dataset.resources.remove(resource)
        dataset.save()
        return '', 204


class DatasetIssuesAPI(IssuesAPI):
    model = DatasetIssue


api.add_resource(DatasetListAPI, '/datasets/', endpoint=b'api.datasets')
api.add_resource(DatasetAPI, '/datasets/<string:slug>', endpoint=b'api.dataset')
api.add_resource(DatasetFeaturedAPI, '/datasets/<string:slug>/featured', endpoint=b'api.dataset_featured')
api.add_resource(ResourcesAPI, '/datasets/<string:slug>/resources', endpoint=b'api.resources')
api.add_resource(ResourceAPI, '/datasets/<string:slug>/resources/<string:rid>', endpoint=b'api.resource')
api.add_resource(DatasetIssuesAPI, '/datasets/<id>/issues/', endpoint=b'api.dataset_issues')
