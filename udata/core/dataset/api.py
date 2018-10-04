# -*- coding: utf-8 -*-
'''
TODO: We need to cleanup and give more coherence to these APIs
- upload enpoints should be singular instead of plural
- community resource APIs should be consistent
    (single root instead of the current state splitted
    between /dataset/<id>/community and /community_resource/)
- Swagger operation IDs needs to be explicits
- make use of latest RESTPlus decorator:
  - @api.expect
  - @api.param
- permissions needs to be more comprehensible
- some mutualizations may be removed (common_doc ?)
- some API need to renaming (ie. featured vs moderated...)

These changes might lead to backward compatibility breakage meaning:
- new API version
- admin changes
'''
from __future__ import unicode_literals
import os
import logging
from datetime import datetime

from flask import request, current_app
from flask_security import current_user

from udata import search
from udata.auth import admin_permission
from udata.api import api, API, errors
from udata.core import storages
from udata.core.storages.api import handle_upload, upload_parser
from udata.core.badges import api as badges_api
from udata.core.followers.api import FollowAPI
from udata.utils import get_by, multi_to_dict

from .api_fields import (
    community_resource_fields,
    community_resource_page_fields,
    dataset_fields,
    dataset_page_fields,
    dataset_suggestion_fields,
    frequency_fields,
    license_fields,
    resource_fields,
    resource_type_fields,
    upload_fields,
)
from udata.linkchecker.checker import check_resource
from .models import (
    Dataset, Resource, Checksum, License, UPDATE_FREQUENCIES,
    CommunityResource, RESOURCE_TYPES
)
from .permissions import DatasetEditPermission, ResourceEditPermission
from .forms import (
    ResourceForm, DatasetForm, CommunityResourceForm, ResourcesListForm
)
from .search import DatasetSearch

log = logging.getLogger(__name__)

ns = api.namespace('datasets', 'Dataset related operations')
search_parser = DatasetSearch.as_request_parser()
community_parser = api.parser()
community_parser.add_argument(
    'sort', type=str, default='-created', location='args',
    help='The sorting attribute')
community_parser.add_argument(
    'page', type=int, default=1, location='args', help='The page to fetch')
community_parser.add_argument(
    'page_size', type=int, default=20, location='args',
    help='The page size to fetch')
community_parser.add_argument(
    'organization', type=str,
    help='Filter activities for that particular organization',
    location='args')
community_parser.add_argument(
    'dataset', type=str,
    help='Filter activities for that particular dataset',
    location='args')
community_parser.add_argument(
    'owner', type=str,
    help='Filter activities for that particular user',
    location='args')

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
        search_parser.parse_args()
        return search.query(Dataset, **multi_to_dict(request.args))

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
        if dataset.deleted and not DatasetEditPermission(dataset).can():
            api.abort(410, 'Dataset has been deleted')
        return dataset

    @api.secure
    @api.doc('update_dataset')
    @api.expect(dataset_fields)
    @api.marshal_with(dataset_fields)
    @api.response(400, errors.VALIDATION_ERROR)
    def put(self, dataset):
        '''Update a dataset given its identifier'''
        request_deleted = request.json.get('deleted', True)
        if dataset.deleted and request_deleted is not None:
            api.abort(410, 'Dataset has been deleted')
        DatasetEditPermission(dataset).test()
        dataset.last_modified = datetime.now()
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
        dataset.last_modified = datetime.now()
        dataset.save()
        return '', 204


@ns.route('/<dataset:dataset>/featured/', endpoint='dataset_featured')
@api.doc(**common_doc)
class DatasetFeaturedAPI(API):
    @api.secure(admin_permission)
    @api.doc('feature_dataset')
    @api.marshal_with(dataset_fields)
    def post(self, dataset):
        '''Mark the dataset as featured'''
        dataset.featured = True
        dataset.save()
        return dataset

    @api.secure(admin_permission)
    @api.doc('unfeature_dataset')
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
        return Dataset.__badges__


@ns.route('/<dataset:dataset>/badges/', endpoint='dataset_badges')
class DatasetBadgesAPI(API):
    @api.doc('add_dataset_badge', **common_doc)
    @api.expect(badges_api.badge_fields)
    @api.marshal_with(badges_api.badge_fields)
    @api.secure(admin_permission)
    def post(self, dataset):
        '''Create a new badge for a given dataset'''
        return badges_api.add(dataset)


@ns.route('/<dataset:dataset>/badges/<badge_kind>/', endpoint='dataset_badge')
class DatasetBadgeAPI(API):
    @api.doc('delete_dataset_badge', **common_doc)
    @api.secure(admin_permission)
    def delete(self, dataset, badge_kind):
        '''Delete a badge for a given dataset'''
        return badges_api.remove(dataset, badge_kind)


@ns.route('/<dataset:dataset>/resources/', endpoint='resources')
class ResourcesAPI(API):
    @api.secure
    @api.doc('create_resource', body=resource_fields, **common_doc)
    @api.marshal_with(resource_fields)
    def post(self, dataset):
        '''Create a new resource for a given dataset'''
        ResourceEditPermission(dataset).test()
        form = api.validate(ResourceForm)
        resource = Resource()
        form.populate_obj(resource)
        dataset.add_resource(resource)
        dataset.last_modified = datetime.now()
        dataset.save()
        return resource, 201

    @api.secure
    @api.doc('update_resources', **common_doc)
    @api.expect([resource_fields])
    @api.marshal_list_with(resource_fields)
    def put(self, dataset):
        '''Reorder resources'''
        ResourceEditPermission(dataset).test()
        data = {'resources': request.json}
        form = ResourcesListForm.from_json(data, obj=dataset, instance=dataset,
                                           csrf_enabled=False)
        if not form.validate():
            api.abort(400, errors=form.errors['resources'])

        dataset = form.save()
        return dataset.resources, 200


class UploadMixin(object):
    def handle_upload(self, dataset):
        prefix = '/'.join((dataset.slug,
                           datetime.now().strftime('%Y%m%d-%H%M%S')))
        infos = handle_upload(storages.resources, prefix)
        if 'html' in infos['mime']:
            api.abort(415, 'Incorrect file content type: HTML')
        infos['title'] = os.path.basename(infos['filename'])
        infos['checksum'] = Checksum(type='sha1', value=infos.pop('sha1'))
        infos['filesize'] = infos.pop('size')
        del infos['filename']
        return infos


@ns.route('/<dataset:dataset>/upload/', endpoint='upload_new_dataset_resource')
@api.doc(**common_doc)
class UploadNewDatasetResource(UploadMixin, API):
    @api.secure
    @api.doc('upload_new_dataset_resource')
    @api.expect(upload_parser)
    @api.marshal_with(upload_fields)
    def post(self, dataset):
        '''Upload a new dataset resource'''
        ResourceEditPermission(dataset).test()
        infos = self.handle_upload(dataset)
        resource = Resource(**infos)
        dataset.add_resource(resource)
        dataset.last_modified = datetime.now()
        dataset.save()
        return resource, 201


@ns.route('/<dataset:dataset>/upload/community/',
          endpoint='upload_new_community_resource')
@api.doc(**common_doc)
class UploadNewCommunityResources(UploadMixin, API):
    @api.secure
    @api.doc('upload_new_community_resource')
    @api.expect(upload_parser)
    @api.marshal_with(upload_fields)
    def post(self, dataset):
        '''Upload a new community resource'''
        infos = self.handle_upload(dataset)
        infos['owner'] = current_user._get_current_object()
        community_resource = CommunityResource.objects.create(**infos)
        return community_resource, 201


class ResourceMixin(object):

    def get_resource_or_404(self, dataset, id):
        resource = get_by(dataset.resources, 'id', id)
        if not resource:
            api.abort(404, 'Ressource does not exists')
        return resource


@ns.route('/<dataset:dataset>/resources/<uuid:rid>/upload/',
          endpoint='upload_dataset_resource', doc=common_doc)
@api.doc(params={'rid': 'The resource unique identifier'})
class UploadDatasetResource(ResourceMixin, UploadMixin, API):
    @api.secure
    @api.doc('upload_dataset_resource')
    @api.marshal_with(upload_fields)
    def post(self, dataset, rid):
        '''Upload a file related to a given resource on a given dataset'''
        ResourceEditPermission(dataset).test()
        resource = self.get_resource_or_404(dataset, rid)
        infos = self.handle_upload(dataset)
        for k, v in infos.items():
            resource[k] = v
        dataset.update_resource(resource)
        dataset.last_modified = datetime.now()
        dataset.save()
        return resource


@ns.route('/community_resources/<crid:community>/upload/',
          endpoint='upload_community_resource', doc=common_doc)
@api.doc(params={'community': 'The community resource unique identifier'})
class ReuploadCommunityResource(ResourceMixin, UploadMixin, API):
    @api.secure
    @api.doc('upload_community_resource')
    @api.marshal_with(upload_fields)
    def post(self, community):
        '''Update the file related to a given community resource'''
        ResourceEditPermission(community).test()
        infos = self.handle_upload(community.dataset)
        community.update(**infos)
        community.reload()
        return community


@ns.route('/<dataset:dataset>/resources/<uuid:rid>/', endpoint='resource',
          doc=common_doc)
@api.doc(params={'rid': 'The resource unique identifier'})
class ResourceAPI(ResourceMixin, API):
    @api.doc('get_resource')
    @api.marshal_with(resource_fields)
    def get(self, dataset, rid):
        '''Get a resource given its identifier'''
        if dataset.deleted and not DatasetEditPermission(dataset).can():
            api.abort(410, 'Dataset has been deleted')
        resource = self.get_resource_or_404(dataset, rid)
        return resource

    @api.secure
    @api.doc('update_resource', body=resource_fields)
    @api.marshal_with(resource_fields)
    def put(self, dataset, rid):
        '''Update a given resource on a given dataset'''
        ResourceEditPermission(dataset).test()
        resource = self.get_resource_or_404(dataset, rid)
        form = api.validate(ResourceForm, resource)
        form.populate_obj(resource)
        resource.modified = datetime.now()
        dataset.last_modified = datetime.now()
        dataset.save()
        return resource

    @api.secure
    @api.doc('delete_resource')
    def delete(self, dataset, rid):
        '''Delete a given resource on a given dataset'''
        ResourceEditPermission(dataset).test()
        resource = self.get_resource_or_404(dataset, rid)
        dataset.resources.remove(resource)
        dataset.last_modified = datetime.now()
        dataset.save()
        return '', 204


@ns.route('/community_resources/', endpoint='community_resources')
class CommunityResourcesAPI(API):
    @api.doc('list_community_resources')
    @api.marshal_with(community_resource_page_fields)
    @api.doc(parser=community_parser)
    def get(self):
        '''List all community resources'''
        args = community_parser.parse_args()
        community_resources = CommunityResource.objects
        if args['owner']:
            community_resources = community_resources(owner=args['owner'])
        if args['dataset']:
            community_resources = community_resources(dataset=args['dataset'])
        if args['organization']:
            community_resources = community_resources(
                organization=args['organization'])
        return (community_resources.order_by(args['sort'])
                                   .paginate(args['page'], args['page_size']))

    @api.secure
    @api.doc('create_community_resource')
    @api.expect(community_resource_fields)
    @api.marshal_with(community_resource_fields)
    def post(self):
        '''Create a new community resource'''
        form = api.validate(CommunityResourceForm)
        resource = CommunityResource()
        form.populate_obj(resource)
        if not resource.dataset:
            api.abort(400, errors={
                'dataset': 'A dataset identifier is required'
            })
        if not resource.organization:
            resource.owner = current_user._get_current_object()
        resource.modified = datetime.now()
        resource.save()
        return resource, 201


@ns.route('/community_resources/<crid:community>/',
          endpoint='community_resource', doc=common_doc)
@api.doc(params={'community': 'The community resource unique identifier'})
class CommunityResourceAPI(API):
    @api.doc('retrieve_community_resource')
    @api.marshal_with(community_resource_fields)
    def get(self, community):
        '''Retrieve a community resource given its identifier'''
        return community

    @api.secure
    @api.doc('update_community_resource',
             body=community_resource_fields)
    @api.marshal_with(community_resource_fields)
    def put(self, community):
        '''Update a given community resource'''
        ResourceEditPermission(community).test()
        form = api.validate(CommunityResourceForm, community)
        form.populate_obj(community)
        if not community.organization:
            community.owner = current_user._get_current_object()
        community.modified = datetime.now()
        community.save()
        return community

    @api.secure
    @api.doc('delete_community_resource')
    @api.marshal_with(community_resource_fields)
    def delete(self, community):
        '''Delete a given community resource'''
        ResourceEditPermission(community).test()
        community.delete()
        return '', 204


@ns.route('/<id>/followers/', endpoint='dataset_followers')
@ns.doc(get={'id': 'list_dataset_followers'},
        post={'id': 'follow_dataset'},
        delete={'id': 'unfollow_dataset'})
class DatasetFollowersAPI(FollowAPI):
    model = Dataset


suggest_parser = api.parser()
suggest_parser.add_argument(
    'q', help='The string to autocomplete/suggest', location='args',
    required=True)
suggest_parser.add_argument(
    'size', type=int, help='The amount of suggestion to fetch',
    location='args', default=10)


@ns.route('/suggest/', endpoint='suggest_datasets')
class SuggestDatasetsAPI(API):
    @api.marshal_list_with(dataset_suggestion_fields)
    @api.doc('suggest_datasets', parser=suggest_parser)
    def get(self):
        '''Suggest datasets'''
        args = suggest_parser.parse_args()
        return [
            {
                'id': opt['payload']['id'],
                'title': opt['text'],
                'acronym': opt['payload'].get('acronym'),
                'score': opt['score'],
                'slug': opt['payload']['slug'],
                'image_url': opt['payload']['image_url'],
            }
            for opt in search.suggest(args['q'], 'dataset_suggest',
                                      args['size'])
        ]


@ns.route('/suggest/formats/', endpoint='suggest_formats')
class SuggestFormatsAPI(API):
    @api.doc('suggest_formats', parser=suggest_parser)
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


@ns.route('/extensions/', endpoint='allowed_extensions')
class AllowedExtensionsAPI(API):
    @api.doc('allowed_extensions')
    @api.response(200, 'Success', [str])
    def get(self):
        '''List all allowed resources extensions'''
        return current_app.config['ALLOWED_RESOURCES_EXTENSIONS']


@ns.route('/<dataset:dataset>/resources/<uuid:rid>/check/',
          endpoint='check_dataset_resource', doc=common_doc)
@api.doc(params={'rid': 'The resource unique identifier'})
class CheckDatasetResource(API, ResourceMixin):

    @api.doc('check_dataset_resource')
    def get(self, dataset, rid):
        '''Checks that a resource's URL exists and returns metadata.'''
        resource = self.get_resource_or_404(dataset, rid)
        return check_resource(resource)


@ns.route('/resource_types/', endpoint='resource_types')
class ResourceTypesAPI(API):
    @api.doc('resource_types')
    @api.marshal_list_with(resource_type_fields)
    def get(self):
        '''List all resource types'''
        return [{'id': id, 'label': label}
                for id, label in RESOURCE_TYPES.items()]
