# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import json
import os
import time
from datetime import datetime

import requests
from flask import request, current_app
from flask.ext.security import current_user

from uuid import UUID
from werkzeug.datastructures import FileStorage

from udata import fileutils, search
from udata.auth import admin_permission
from udata.api import api, fields, SingleObjectAPI, API
from udata.core import storages
from udata.core.followers.api import FollowAPI
from udata.utils import get_by, multi_to_dict

from .api_fields import (
    badge_fields,
    dataset_fields,
    dataset_page_fields,
    dataset_suggestion_fields,
    frequency_fields,
    license_fields,
    resource_fields,
    upload_fields,
)
from .models import (
    Dataset, DatasetBadge, Resource, FollowDataset, Checksum, License,
    DATASET_BADGE_KINDS, UPDATE_FREQUENCIES
)
from .permissions import DatasetEditPermission
from .forms import BadgeForm, ResourceForm, DatasetForm
from .search import DatasetSearch

ns = api.namespace('datasets', 'Dataset related operations')
search_parser = api.search_parser(DatasetSearch)


common_doc = {
    'params': {'dataset': 'The dataset ID or slug'}
}


@ns.route('/', endpoint='datasets')
class DatasetListAPI(API):
    '''Datasets collection endpoint'''
    @api.doc('list_datasets', parser=search_parser)
    @api.marshal_with(dataset_page_fields)
    def get(self):
        '''List or search all datasets'''
        return search.query(DatasetSearch, **multi_to_dict(request.args))

    @api.secure
    @api.doc('create_dataset', responses={400: 'Validation error'})
    @api.expect(dataset_fields)
    @api.marshal_with(dataset_fields)
    def post(self):
        '''Create a new dataset'''
        form = api.validate(DatasetForm)
        dataset = form.save()
        return dataset, 201


@ns.route('/<dataset:dataset>/', endpoint='dataset', doc=common_doc)
@api.response(404, 'Dataset not found')
@api.response(410, 'Dataset has been deleted')
class DatasetAPI(API):
    @api.doc('get_dataset')
    @api.marshal_with(dataset_fields)
    def get(self, dataset):
        '''Get a dataset given its identifier'''
        if dataset.deleted:
            api.abort(410, 'Dataset has been deleted')
        return dataset

    @api.secure
    @api.doc('update_dataset')
    @api.expect(dataset_fields)
    @api.marshal_with(dataset_fields)
    @api.response(400, 'Validation error')
    def put(self, dataset):
        '''Update a dataset given its identifier'''
        if dataset.deleted:
            api.abort(410, 'Dataset has been deleted')
        DatasetEditPermission(dataset).test()
        form = api.validate(DatasetForm, dataset)
        return form.save()

    @api.secure
    @api.doc('delete_dataset')
    @api.response(204, 'Dataset deleted')
    def delete(self, dataset):
        '''Delete a dataset given its identifier'''
        if dataset.deleted:
            api.abort(410, 'Dataset has been deleted')
        DatasetEditPermission(dataset).test()
        dataset.deleted = datetime.now()
        dataset.save()
        return '', 204


@ns.route('/<dataset:dataset>/featured/', endpoint='dataset_featured')
@api.doc(**common_doc)
class DatasetFeaturedAPI(SingleObjectAPI, API):
    model = Dataset

    @api.secure(admin_permission)
    @api.doc('feature_dataset')
    @api.marshal_with(dataset_fields)
    def post(self, dataset):
        '''Mark the dataset as featured'''
        dataset.featured = True
        dataset.save()
        return dataset

    @api.secure(admin_permission)
    @api.doc('unfeature_reuse')
    @api.marshal_with(dataset_fields)
    def delete(self, dataset):
        '''Unmark the dataset as featured'''
        dataset.featured = False
        dataset.save()
        return dataset


@ns.route('/badges/', endpoint='available_dataset_badges')
class AvailableDatasetBadgesAPI(API):
    @api.doc('available_dataset_badges')
    def get(self):
        '''List all available dataset badges and their labels'''
        return DATASET_BADGE_KINDS


@ns.route('/<dataset:dataset>/badges/', endpoint='dataset_badges')
class DatasetBadgesAPI(API):
    @api.doc('add_dataset_badge', **common_doc)
    @api.expect(badge_fields)
    @api.marshal_with(badge_fields)
    @api.secure(admin_permission)
    def post(self, dataset):
        '''Create a new badge for a given dataset'''
        form = api.validate(BadgeForm)
        badge = DatasetBadge(created=datetime.now(),
                             created_by=current_user.id)
        form.populate_obj(badge)
        for existing_badge in dataset.badges:
            if existing_badge.kind == badge.kind:
                return existing_badge
        dataset.add_badge(badge)
        return badge, 201


@ns.route('/<dataset:dataset>/badges/<badge_kind>/', endpoint='dataset_badge')
class DatasetBadgeAPI(API):
    @api.doc('delete_dataset_badge', **common_doc)
    @api.secure(admin_permission)
    def delete(self, dataset, badge_kind):
        '''Delete a badge for a given dataset'''
        badge = None
        for badge in dataset.badges:
            if badge.kind == badge_kind:
                break
        if badge is None:
            api.abort(404, 'Badge does not exists')
        dataset.remove_badge(badge)
        return '', 204


@ns.route('/<dataset:dataset>/resources/', endpoint='resources')
class ResourcesAPI(API):
    @api.secure
    @api.doc(id='create_resource', body=resource_fields, **common_doc)
    @api.marshal_with(resource_fields)
    def post(self, dataset):
        '''Create a new resource for a given dataset'''
        DatasetEditPermission(dataset).test()
        form = api.validate(ResourceForm)
        resource = Resource()
        form.populate_obj(resource)
        dataset.add_resource(resource)
        return resource, 201

    @api.secure
    @api.doc('reorder_resources', **common_doc)
    @api.expect([fields.String])
    @api.marshal_with(resource_fields)
    def put(self, dataset):
        '''Reorder resources'''
        DatasetEditPermission(dataset).test()
        new_resources = []
        for rid in request.json:
            resource = get_by(dataset.resources, 'id', UUID(rid))
            new_resources.append(resource)
        dataset.resources = new_resources
        dataset.save()
        return dataset.resources, 200


upload_parser = api.parser()
upload_parser.add_argument('file', type=FileStorage, location='files')


@ns.route('/<dataset:dataset>/upload/', endpoint='upload_resource')
@api.doc(parser=upload_parser, **common_doc)
class UploadResource(API):
    @api.secure
    @api.doc(id='upload_resource')
    @api.marshal_with(upload_fields)
    def post(self, dataset):
        '''Upload a new resource'''
        DatasetEditPermission(dataset).test()
        args = upload_parser.parse_args()

        storage = storages.resources

        prefix = self.get_prefix(dataset)

        file = args['file']
        filename = storage.save(file, prefix=prefix)

        extension = fileutils.extension(filename)

        file.seek(0)
        sha1 = storages.utils.sha1(file)

        size = (os.path.getsize(storage.path(filename))
                if storage.root else None)

        resource = Resource(
            title=os.path.basename(filename),
            url=storage.url(filename, external=True),
            checksum=Checksum(value=sha1),
            format=extension,
            mime=storages.utils.mime(filename),
            size=size
        )
        dataset.add_resource(resource)
        return resource, 201

    def get_prefix(self, dataset):
        return '/'.join((dataset.slug,
                         datetime.now().strftime('%Y%m%d-%H%M%S')))


@ns.route('/<dataset:dataset>/resources/<uuid:rid>/', endpoint='resource',
          doc=common_doc)
@api.doc(params={'rid': 'The resource unique identifier'})
class ResourceAPI(API):
    def get_resource_or_404(self, dataset, id):
        resource = get_by(dataset.resources, 'id', id)
        if not resource:
            api.abort(404, 'Ressource does not exists')
        return resource

    @api.secure
    @api.doc(id='update_resource', body=resource_fields)
    @api.marshal_with(resource_fields)
    def put(self, dataset, rid):
        '''Update a given resource on a given dataset'''
        DatasetEditPermission(dataset).test()
        resource = self.get_resource_or_404(dataset, rid)
        form = api.validate(ResourceForm, resource)
        form.populate_obj(resource)
        resource.modified = datetime.now()
        dataset.save()
        return resource

    @api.secure
    @api.doc('delete_resource')
    def delete(self, dataset, rid):
        '''Delete a given resource on a given dataset'''
        DatasetEditPermission(dataset).test()
        resource = self.get_resource_or_404(dataset, rid)
        dataset.resources.remove(resource)
        dataset.save()
        return '', 204


@ns.route('/<id>/followers/', endpoint='dataset_followers')
class DatasetFollowersAPI(FollowAPI):
    model = FollowDataset


suggest_parser = api.parser()
suggest_parser.add_argument(
    'q', type=unicode, help='The string to autocomplete/suggest',
    location='args', required=True)
suggest_parser.add_argument(
    'size', type=int, help='The amount of suggestion to fetch',
    location='args', default=10)


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
            for opt in search.suggest(args['q'], 'dataset_suggest',
                                      args['size'])
        ]


@ns.route('/suggest/formats/', endpoint='suggest_formats')
class SuggestFormatsAPI(API):
    @api.doc(id='suggest_formats', parser=suggest_parser)
    def get(self):
        '''Suggest file formats'''
        args = suggest_parser.parse_args()
        result = search.suggest(args['q'], 'format_suggest', args['size'])
        return sorted(result, key=lambda o: len(o['text']))


@ns.route('/licenses/', endpoint='licenses')
class LicensesAPI(API):
    @api.doc('list_licenses')
    @api.marshal_list_with(license_fields)
    def get(self):
        '''List all available licenses'''
        return list(License.objects)


@ns.route('/frequencies/', endpoint='dataset_frequencies')
class FrequenciesAPI(API):
    @api.doc('list_frequencies')
    @api.marshal_list_with(frequency_fields)
    def get(self):
        '''List all available frequencies'''
        return [{'id': id, 'label': label}
                for id, label in UPDATE_FREQUENCIES.items()]


checkurl_parser = api.parser()
checkurl_parser.add_argument('url', type=unicode, help='The URL to check',
                             location='args', required=True)


@ns.route('/checkurl/', endpoint='checkurl')
class CheckUrlAPI(API):

    @api.doc(id='checkurl', parser=checkurl_parser)
    def get(self):
        '''Checks that a URL exists and returns metadata.'''
        args = checkurl_parser.parse_args()
        CROQUEMORT = current_app.config.get('CROQUEMORT')
        if CROQUEMORT is None:
            return {'error': 'Check server not configured.'}, 500
        check_url = '{url}/check/one'.format(url=CROQUEMORT['url'])
        response = requests.post(check_url,
                                 data=json.dumps({'url': args['url']}))
        url_hash = response.json()['url-hash']
        retrieve_url = '{url}/url/{url_hash}'.format(
            url=CROQUEMORT['url'], url_hash=url_hash)
        response = requests.get(retrieve_url, params={'url': args['url']})
        attempts = 0
        while response.status_code == 404 or 'status' not in response.json():
            if attempts >= CROQUEMORT['retry']:
                msg = ('We were unable to retrieve the URL after'
                       ' {attempts} attempts.').format(attempts=attempts)
                return {'error': msg}, 502
            response = requests.get(retrieve_url, params={'url': args['url']})
            time.sleep(CROQUEMORT['delay'])
            attempts += 1
        result = response.json()
        if int(result['status']) > 500:
            return result, 500
        return result
