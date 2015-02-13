# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime

from flask import request

from uuid import UUID

from udata import search
from udata.api import api, ModelAPI, ModelListAPI, SingleObjectAPI, API
from udata.core.issues.api import IssuesAPI
from udata.core.followers.api import FollowAPI
from udata.utils import get_by

from .api_fields import resource_fields, dataset_fields, dataset_page_fields, dataset_suggestion_fields, resources_order
from .models import Dataset, Resource, DatasetIssue, FollowDataset
from .forms import DatasetForm, ResourceForm, DatasetFullForm
from .search import DatasetSearch

ns = api.namespace('datasets', 'Dataset related operations')
search_parser = api.search_parser(DatasetSearch)


common_doc = {
    'params': {'dataset': 'The dataset ID or slug'}
}


@ns.route('/', endpoint='datasets')
@api.doc(get={'id': 'list_datasets', 'model': dataset_page_fields, 'parser': search_parser})
@api.doc(post={'id': 'create_dataset', 'model': dataset_fields, 'body': dataset_fields})
class DatasetListAPI(ModelListAPI):
    model = Dataset
    form = DatasetFullForm
    fields = dataset_fields
    search_adapter = DatasetSearch


@ns.route('/<dataset:dataset>/', endpoint='dataset', doc=common_doc)
@api.doc(model=dataset_fields)
@api.doc(get={'id': 'get_dataset'})
@api.doc(put={'id': 'update_dataset'})
class DatasetAPI(ModelAPI):
    model = Dataset
    form = DatasetForm
    fields = dataset_fields


@ns.route('/<dataset:dataset>/featured/', endpoint='dataset_featured')
@api.doc(**common_doc)
class DatasetFeaturedAPI(SingleObjectAPI, API):
    model = Dataset

    @api.secure
    @api.doc(id='feature_dataset')
    @api.marshal_with(dataset_fields)
    def post(self, dataset):
        '''Mark the dataset as featured'''
        dataset.featured = True
        dataset.save()
        return dataset

    @api.secure
    @api.doc(id='unfeature_reuse')
    @api.marshal_with(dataset_fields)
    def delete(self, dataset):
        '''Unmark the dataset as featured'''
        dataset.featured = False
        dataset.save()
        return dataset


@ns.route('/<dataset:dataset>/resources/', endpoint='resources', doc=common_doc)
class ResourcesAPI(API):
    @api.secure
    @api.doc(id='create_resource')
    @api.marshal_with(resource_fields)
    def post(self, dataset):
        '''Create a new resource for a given dataset'''
        form = api.validate(ResourceForm)
        resource = Resource()
        form.populate_obj(resource)
        dataset.resources.append(resource)
        dataset.save()
        return resource, 201

    @api.secure
    @api.doc(id='update_resources', **common_doc)
    # @api.doc(body=resources_order)
    @api.marshal_with(resource_fields)
    def put(self, dataset):
        '''Update all ressources the same time'''
        new_resources = []
        for rid in request.json:
            resource = get_by(dataset.resources, 'id', UUID(rid))
            new_resources.append(resource)
        dataset.resources = new_resources
        dataset.save()
        return dataset.resources, 200


@ns.route('/<dataset:dataset>/resources/<uuid:rid>/', endpoint='resource', doc=common_doc)
@api.doc(params={'rid': 'The resource unique identifier'})
class ResourceAPI(API):
    def get_resource_or_404(self, dataset, id):
        resource = get_by(dataset.resources, 'id', id)
        if not resource:
            api.abort(404, 'Ressource does not exists')
        return resource

    @api.secure
    @api.doc(id='update_resource')
    @api.marshal_with(resource_fields)
    def put(self, dataset, rid):
        '''Update a given resource on a given dataset'''
        resource = self.get_resource_or_404(dataset, rid)
        form = api.validate(ResourceForm, resource)
        form.populate_obj(resource)
        resource.modified = datetime.now()
        dataset.save()
        return resource

    @api.secure
    @api.doc(id='delete_resource')
    def delete(self, dataset, rid):
        '''Delete a given resource on a given dataset'''
        resource = self.get_resource_or_404(dataset, rid)
        dataset.resources.remove(resource)
        dataset.save()
        return '', 204


@ns.route('/<id>/issues/', endpoint='dataset_issues')
@api.doc(params={'id': 'The dataset ID'})
class DatasetIssuesAPI(IssuesAPI):
    model = DatasetIssue


@ns.route('/<id>/followers/', endpoint='dataset_followers')
class DatasetFollowersAPI(FollowAPI):
    model = FollowDataset


suggest_parser = api.parser()
suggest_parser.add_argument('q', type=unicode, help='The string to autocomplete/suggest', location='args', required=True)
suggest_parser.add_argument('size', type=int, help='The amount of suggestion to fetch', location='args', default=10)


@ns.route('/suggest/', endpoint='suggest_datasets')
class SuggestDatasetsAPI(API):
    @api.marshal_list_with(dataset_suggestion_fields)
    @api.doc(id='suggest_datasets', parser=suggest_parser)
    def get(self):
        '''Suggest datasets'''
        args = suggest_parser.parse_args()
        return [
            {
                'id': opt['payload']['id'],
                'title': opt['text'],
                'score': opt['score'],
                'slug': opt['payload']['slug'],
                'image_url': opt['payload']['image_url'],
            }
            for opt in search.suggest(args['q'], 'dataset_suggest', args['size'])
        ]


@ns.route('/suggest/formats/', endpoint='suggest_formats')
class SuggestFormatsAPI(API):
    @api.doc(id='suggest_formats', parser=suggest_parser)
    def get(self):
        '''Suggest file formats'''
        args = suggest_parser.parse_args()
        result = search.suggest(args['q'], 'format_suggest', args['size'])
        return sorted(result, key=lambda o: len(o['text']))
