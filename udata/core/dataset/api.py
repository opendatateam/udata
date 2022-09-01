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

import os
import logging
from datetime import datetime

from flask import request, current_app, abort, redirect, url_for, make_response
from flask_security import current_user
from mongoengine.queryset.visitor import Q

from udata.auth import admin_permission
from udata.api import api, API, errors
from udata.api.parsers import ModelApiParser
from udata.core import storages
from udata.core.storages.api import handle_upload, upload_parser
from udata.core.badges import api as badges_api
from udata.core.followers.api import FollowAPI
from udata.utils import get_by
from udata.rdf import (
    RDF_EXTENSIONS,
    negociate_content, graph_response
)

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
    schema_fields,
)
from udata.linkchecker.checker import check_resource
from .models import (
    Dataset, Resource, Checksum, License, UPDATE_FREQUENCIES,
    CommunityResource, RESOURCE_TYPES, ResourceSchema, get_resource
)
from .permissions import DatasetEditPermission, ResourceEditPermission
from .forms import (
    ResourceForm, DatasetForm, CommunityResourceForm, ResourcesListForm
)
from .exceptions import (
    SchemasCatalogNotFoundException, SchemasCacheUnavailableException
)
from .rdf import dataset_to_rdf


DEFAULT_SORTING = '-created_at'
SUGGEST_SORTING = '-metrics.followers'


class DatasetApiParser(ModelApiParser):
    sorts = {
        'title': 'title',
        'created': 'created_at',
        'last_modified': 'last_modified',
        'reuses': 'metrics.reuses',
        'followers': 'metrics.followers',
        'views': 'metrics.views',
    }

    def __init__(self):
        super().__init__()
        self.parser.add_argument('tag', type=str, location='args')
        self.parser.add_argument('license', type=str, location='args')
        self.parser.add_argument('featured', type=bool, location='args')
        self.parser.add_argument('geozone', type=str, location='args')
        self.parser.add_argument('granularity', type=str, location='args')
        self.parser.add_argument('temporal_coverage', type=str, location='args')
        self.parser.add_argument('organization', type=str, location='args')
        self.parser.add_argument('owner', type=str, location='args')
        self.parser.add_argument('format', type=str, location='args')
        self.parser.add_argument('schema', type=str, location='args')
        self.parser.add_argument('schema_version', type=str, location='args')

    @staticmethod
    def parse_filters(datasets, args):
        if args.get('q'):
            # Following code splits the 'q' argument by spaces to surround
            # every word in it with quotes before rebuild it.
            # This allows the search_text method to tokenise with an AND
            # between tokens whereas an OR is used without it.
            phrase_query = ' '.join([f'"{elem}"' for elem in args['q'].split(' ')])
            datasets = datasets.search_text(phrase_query)
        if args.get('tag'):
            datasets = datasets.filter(tags=args['tag'])
        if args.get('license'):
            datasets = datasets.filter(license__in=License.objects.filter(id=args['license']))
        if args.get('geozone'):
            datasets = datasets.filter(spatial__zones=args['geozone'])
        if args.get('granularity'):
            datasets = datasets.filter(spatial__granularity=args['granularity'])
        if args.get('temporal_coverage'):
            datasets = datasets.filter(temporal_coverage__start__gte=args['temporal_coverage'][:9], temporal_coverage__start__lte=args['temporal_coverage'][11:])
        if args.get('featured'):
            datasets = datasets.filter(featured=args['featured'])
        if args.get('organization'):
            datasets = datasets.filter(organization=args['organization'])
        if args.get('owner'):
            datasets = datasets.filter(owner=args['owner'])
        if args.get('format'):
            datasets = datasets.filter(resources__format=args['format'])
        if args.get('schema'):
            datasets = datasets.filter(resources__schema__name=args['schema'])
        if args.get('schema_version'):
            datasets = datasets.filter(resources__schema__version=args['schema_version'])
        return datasets


log = logging.getLogger(__name__)

ns = api.namespace('datasets', 'Dataset related operations')

dataset_parser = DatasetApiParser()

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
    @api.doc('list_datasets')
    @api.expect(dataset_parser.parser)
    @api.marshal_with(dataset_page_fields)
    def get(self):
        '''List or search all datasets'''
        args = dataset_parser.parse()
        datasets = Dataset.objects(archived=None, deleted=None, private=False)
        datasets = dataset_parser.parse_filters(datasets, args)

        sort = args['sort'] or ('$text_score' if args['q'] else None) or DEFAULT_SORTING
        return datasets.order_by(sort).paginate(args['page'], args['page_size'])

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


@ns.route('/<dataset:dataset>/rdf', endpoint='dataset_rdf', doc=common_doc)
@api.response(404, 'Dataset not found')
@api.response(410, 'Dataset has been deleted')
class DatasetRdfAPI(API):
    @api.doc('rdf_dataset')
    def get(self, dataset):
        format = RDF_EXTENSIONS[negociate_content()]
        url = url_for('api.dataset_rdf_format', dataset=dataset.id, format=format)
        return redirect(url)


@ns.route('/<dataset:dataset>/rdf.<format>', endpoint='dataset_rdf_format', doc=common_doc)
@api.response(404, 'Dataset not found')
@api.response(410, 'Dataset has been deleted')
class DatasetRdfFormatAPI(API):
    @api.doc('rdf_dataset_format')
    def get(self, dataset, format):
        if not DatasetEditPermission(dataset).can():
            if dataset.private:
                api.abort(404)
            elif dataset.deleted:
                api.abort(410)

        resource = dataset_to_rdf(dataset)
        # bypass flask-restplus make_response, since graph_response
        # is handling the content negociation directly
        return make_response(*graph_response(resource, format))


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


@ns.route('/r/<uuid:id>', endpoint='resource_redirect')
class ResourceRedirectAPI(API):
    @api.doc('redirect_resource', **common_doc)
    def get(self, id):
        '''
        Redirect to the latest version of a resource given its identifier.
        '''
        resource = get_resource(id)
        return redirect(resource.url.strip()) if resource else abort(404)


@ns.route('/<dataset:dataset>/resources/', endpoint='resources')
class ResourcesAPI(API):
    @api.secure
    @api.doc('create_resource', **common_doc)
    @api.expect(resource_fields)
    @api.marshal_with(resource_fields)
    def post(self, dataset):
        '''Create a new resource for a given dataset'''
        ResourceEditPermission(dataset).test()
        form = api.validate(ResourceForm)
        resource = Resource()
        if form._fields.get('filetype').data != 'remote':
            return 'This endpoint only supports remote resources', 400
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
                                           meta={'csrf': False})
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
        infos['dataset'] = dataset
        community_resource = CommunityResource.objects.create(**infos)
        return community_resource, 201


class ResourceMixin(object):

    def get_resource_or_404(self, dataset, id):
        resource = get_by(dataset.resources, 'id', id)
        if not resource:
            api.abort(404, 'Resource does not exist')
        return resource


@ns.route('/<dataset:dataset>/resources/<uuid:rid>/upload/',
          endpoint='upload_dataset_resource', doc=common_doc)
@api.param('rid', 'The resource unique identifier')
class UploadDatasetResource(ResourceMixin, UploadMixin, API):
    @api.secure
    @api.doc('upload_dataset_resource')
    @api.marshal_with(upload_fields)
    def post(self, dataset, rid):
        '''Upload a file related to a given resource on a given dataset'''
        ResourceEditPermission(dataset).test()
        resource = self.get_resource_or_404(dataset, rid)
        fs_filename_to_remove = resource.fs_filename
        infos = self.handle_upload(dataset)
        for k, v in infos.items():
            resource[k] = v
        dataset.update_resource(resource)
        dataset.last_modified = datetime.now()
        dataset.save()
        if fs_filename_to_remove is not None:
            storages.resources.delete(fs_filename_to_remove)
        return resource


@ns.route('/community_resources/<crid:community>/upload/',
          endpoint='upload_community_resource', doc=common_doc)
@api.param('community', 'The community resource unique identifier')
class ReuploadCommunityResource(ResourceMixin, UploadMixin, API):
    @api.secure
    @api.doc('upload_community_resource')
    @api.marshal_with(upload_fields)
    def post(self, community):
        '''Update the file related to a given community resource'''
        ResourceEditPermission(community).test()
        fs_filename_to_remove = community.fs_filename
        infos = self.handle_upload(community.dataset)
        community.update(**infos)
        community.reload()
        if fs_filename_to_remove is not None:
            storages.resources.delete(fs_filename_to_remove)
        return community


@ns.route('/<dataset:dataset>/resources/<uuid:rid>/', endpoint='resource',
          doc=common_doc)
@api.param('rid', 'The resource unique identifier')
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
    @api.doc('update_resource')
    @api.expect(resource_fields)
    @api.marshal_with(resource_fields)
    def put(self, dataset, rid):
        '''Update a given resource on a given dataset'''
        ResourceEditPermission(dataset).test()
        resource = self.get_resource_or_404(dataset, rid)
        form = api.validate(ResourceForm, resource)
        # ensure API client does not override url on self-hosted resources
        if resource.filetype == 'file':
            form._fields.get('url').data = resource.url
        # populate_obj populates existing resource object with the content of the form.
        # update_resource saves the updated resource dict to the database
        # the additional dataset.save is required as we update the last_modified date.
        form.populate_obj(resource)
        resource.modified = datetime.now()
        dataset.update_resource(resource)
        dataset.last_modified = datetime.now()
        dataset.save()
        return resource

    @api.secure
    @api.doc('delete_resource')
    def delete(self, dataset, rid):
        '''Delete a given resource on a given dataset'''
        ResourceEditPermission(dataset).test()
        resource = self.get_resource_or_404(dataset, rid)
        dataset.remove_resource(resource)
        dataset.last_modified = datetime.now()
        dataset.save()
        return '', 204


@ns.route('/community_resources/', endpoint='community_resources')
class CommunityResourcesAPI(API):
    @api.doc('list_community_resources')
    @api.expect(community_parser)
    @api.marshal_with(community_resource_page_fields)
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
        if form._fields.get('filetype').data != 'remote':
            return 'This endpoint only supports remote community resources', 400
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
@api.param('community', 'The community resource unique identifier')
class CommunityResourceAPI(API):
    @api.doc('retrieve_community_resource')
    @api.marshal_with(community_resource_fields)
    def get(self, community):
        '''Retrieve a community resource given its identifier'''
        return community

    @api.secure
    @api.doc('update_community_resource')
    @api.expect(community_resource_fields)
    @api.marshal_with(community_resource_fields)
    def put(self, community):
        '''Update a given community resource'''
        ResourceEditPermission(community).test()
        form = api.validate(CommunityResourceForm, community)
        if community.filetype == 'file':
            form._fields.get('url').data = community.url
        form.populate_obj(community)
        if not community.organization and not community.owner:
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
        # Deletes community resource's file from file storage
        if community.fs_filename is not None:
            storages.resources.delete(community.fs_filename)
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
class DatasetSuggestAPI(API):
    @api.doc('suggest_datasets')
    @api.expect(suggest_parser)
    @api.marshal_with(dataset_suggestion_fields)
    def get(self):
        '''Datasets suggest endpoint using mongoDB contains'''
        args = suggest_parser.parse_args()
        datasets_query = Dataset.objects(archived=None, deleted=None, private=False)
        datasets = datasets_query.filter(Q(title__icontains=args['q']) | Q(acronym__icontains=args['q']))
        return [
            {
                'id': dataset.id,
                'title': dataset.title,
                'acronym': dataset.acronym,
                'slug': dataset.slug,
                'image_url': dataset.organization.logo if dataset.organization else dataset.owner.avatar if dataset.owner else None
            }
            for dataset in datasets.order_by(SUGGEST_SORTING).limit(args['size'])
        ]


@ns.route('/suggest/formats/', endpoint='suggest_formats')
class FormatsSuggestAPI(API):
    @api.doc('suggest_formats')
    @api.expect(suggest_parser)
    def get(self):
        '''Suggest file formats'''
        args = suggest_parser.parse_args()
        results = [{'text': i} for i in current_app.config['ALLOWED_RESOURCES_EXTENSIONS'] if args['q'] in i]
        results = results[:args['size']]
        return sorted(results, key=lambda o: len(o['text']))


@ns.route('/suggest/mime/', endpoint='suggest_mime')
class MimesSuggestAPI(API):
    @api.doc('suggest_mime')
    @api.expect(suggest_parser)
    def get(self):
        '''Suggest mime types'''
        args = suggest_parser.parse_args()
        results = [{'text': i} for i in current_app.config['ALLOWED_RESOURCES_MIMES'] if args['q'] in i]
        results = results[:args['size']]
        return sorted(results, key=lambda o: len(o['text']))


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
@api.param('rid', 'The resource unique identifier')
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


@ns.route('/schemas/', endpoint='schemas')
class SchemasAPI(API):
    @api.doc('schemas')
    @api.marshal_list_with(schema_fields)
    def get(self):
        '''List all available schemas'''
        try:
            # This method call is cached as it makes HTTP requests
            return ResourceSchema.objects()
        except SchemasCacheUnavailableException:
            abort(503, description='No schemas in cache and endpoint unavailable')
        except SchemasCatalogNotFoundException:
            abort(404, description='Schema catalog endpoint was not found')
