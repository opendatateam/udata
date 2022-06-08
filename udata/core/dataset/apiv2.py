import logging

from flask import url_for, request, abort
from flask_restplus import marshal

from udata import search
from udata.api import apiv2, API, fields
from udata.utils import multi_to_dict, get_by

from .api_fields import (
    badge_fields,
    org_ref_fields,
    resource_fields,
    spatial_coverage_fields,
    temporal_coverage_fields,
    user_ref_fields,
    checksum_fields
)
from udata.core.spatial.api_fields import geojson
from .models import (
    Dataset, UPDATE_FREQUENCIES, DEFAULT_FREQUENCY, DEFAULT_LICENSE, CommunityResource
)
from .permissions import DatasetEditPermission
from .search import DatasetSearch

DEFAULT_PAGE_SIZE = 50
DEFAULT_SORTING = '-created_at'

#: Default mask to make it lightweight by default
DEFAULT_MASK_APIV2 = ','.join((
    'id', 'title', 'acronym', 'slug', 'description', 'created_at', 'last_modified', 'deleted',
    'private', 'tags', 'badges', 'resources', 'community_resources', 'frequency', 'frequency_date', 'extras',
    'metrics', 'organization', 'owner', 'temporal_coverage', 'spatial', 'license',
    'uri', 'page', 'last_update', 'archived', 'quality'
))

log = logging.getLogger(__name__)

ns = apiv2.namespace('datasets', 'Dataset related operations')
search_parser = DatasetSearch.as_request_parser()
resources_parser = apiv2.parser()
resources_parser.add_argument(
    'page', type=int, default=1, location='args', help='The page to fetch')
resources_parser.add_argument(
    'page_size', type=int, default=DEFAULT_PAGE_SIZE, location='args',
    help='The page size to fetch')
resources_parser.add_argument(
    'type', type=str, location='args',
    help='The type of resources to fetch')
resources_parser.add_argument(
    'q', type=str, location='args',
    help='query string to search through resources titles')

common_doc = {
    'params': {'dataset': 'The dataset ID or slug'}
}


dataset_fields = apiv2.model('Dataset', {
    'id': fields.String(description='The dataset identifier', readonly=True),
    'title': fields.String(description='The dataset title', required=True),
    'acronym': fields.String(description='An optional dataset acronym'),
    'slug': fields.String(
        description='The dataset permalink string', required=True),
    'description': fields.Markdown(
        description='The dataset description in markdown', required=True),
    'created_at': fields.ISODateTime(
        description='The dataset creation date', required=True),
    'last_modified': fields.ISODateTime(
        description='The dataset last modification date', required=True),
    'deleted': fields.ISODateTime(description='The deletion date if deleted'),
    'archived': fields.ISODateTime(description='The archival date if archived'),
    'featured': fields.Boolean(description='Is the dataset featured'),
    'private': fields.Boolean(
        description='Is the dataset private to the owner or the organization'),
    'tags': fields.List(fields.String),
    'badges': fields.List(fields.Nested(badge_fields),
                          description='The dataset badges',
                          readonly=True),
    'resources': fields.Raw(attribute=lambda o: {
        'rel': 'subsection',
        'href': url_for('apiv2.resources', dataset=o.id, page=1, page_size=DEFAULT_PAGE_SIZE, _external=True),
        'type': 'GET',
        'total': len(o.resources)
        }, description='Link to the dataset resources'),
    'community_resources': fields.Raw(attribute=lambda o: {
        'rel': 'subsection',
        'href': url_for('api.community_resources', dataset=o.id, page=1, page_size=DEFAULT_PAGE_SIZE, _external=True),
        'type': 'GET',
        'total': len(o.community_resources)
        }, description='Link to the dataset community resources'),
    'frequency': fields.String(
        description='The update frequency', required=True,
        enum=list(UPDATE_FREQUENCIES), default=DEFAULT_FREQUENCY),
    'frequency_date': fields.ISODateTime(
        description=('Next expected update date, you will be notified '
                     'once that date is reached.')),
    'extras': fields.Raw(description='Extras attributes as key-value pairs'),
    'metrics': fields.Raw(attribute=lambda o: o.get_metrics(), description='The dataset metrics'),
    'organization': fields.Nested(
        org_ref_fields, allow_null=True,
        description='The producer organization'),
    'owner': fields.Nested(
        user_ref_fields, allow_null=True, description='The user information'),
    'temporal_coverage': fields.Nested(
        temporal_coverage_fields, allow_null=True,
        description='The temporal coverage'),
    'spatial': fields.Nested(
        spatial_coverage_fields, allow_null=True,
        description='The spatial coverage'),
    'license': fields.String(attribute='license.id',
                             default=DEFAULT_LICENSE['id'],
                             description='The dataset license'),
    'uri': fields.UrlFor(
        'api.dataset', lambda o: {'dataset': o},
        description='The dataset API URI', required=True),
    'page': fields.UrlFor(
        'datasets.show', lambda o: {'dataset': o},
        description='The dataset page URL', required=True, fallback_endpoint='api.dataset'),
    'quality': fields.Raw(description='The dataset quality', readonly=True),
    'last_update': fields.ISODateTime(
        description='The resources last modification date', required=True),
}, mask=DEFAULT_MASK_APIV2)


resource_page_fields = apiv2.model('ResourcePage', {
    'data': fields.List(
        fields.Nested(resource_fields, description='The dataset resources')
    ),
    'next_page': fields.String(),
    'previous_page': fields.String(),
    'page': fields.Integer(),
    'page_size': fields.Integer(),
    'total': fields.Integer()
})

dataset_page_fields = apiv2.model(
    'DatasetPage',
    fields.pager(dataset_fields),
    mask='data{{{0}}},*'.format(DEFAULT_MASK_APIV2)
)

specific_resource_fields = apiv2.model('SpecificResource', {
    'resource': fields.Nested(resource_fields, description='The dataset resources'),
    'dataset_id': fields.String()
})

apiv2.inherit('Badge', badge_fields)
apiv2.inherit('OrganizationReference', org_ref_fields)
apiv2.inherit('UserReference', user_ref_fields)
apiv2.inherit('Resource', resource_fields)
apiv2.inherit('SpatialCoverage', spatial_coverage_fields)
apiv2.inherit('TemporalCoverage', temporal_coverage_fields)
apiv2.inherit('GeoJSON', geojson)
apiv2.inherit('Checksum', checksum_fields)


@ns.route('/search/', endpoint='dataset_search')
class DatasetSearchAPI(API):
    '''Datasets collection search endpoint'''
    @apiv2.doc('search_datasets')
    @apiv2.expect(search_parser)
    @apiv2.marshal_with(dataset_page_fields)
    def get(self):
        '''List or search all datasets'''
        search_parser.parse_args()
        try:
            return search.query(Dataset, **multi_to_dict(request.args))
        except NotImplementedError:
            abort(501, 'Search endpoint not enabled')
        except RuntimeError:
            abort(500, 'Internal search service error')


@ns.route('/<dataset:dataset>/', endpoint='dataset', doc=common_doc)
@apiv2.response(404, 'Dataset not found')
@apiv2.response(410, 'Dataset has been deleted')
class DatasetAPI(API):
    @apiv2.doc('get_dataset')
    @apiv2.marshal_with(dataset_fields)
    def get(self, dataset):
        '''Get a dataset given its identifier'''
        if dataset.deleted and not DatasetEditPermission(dataset).can():
            apiv2.abort(410, 'Dataset has been deleted')
        return dataset


@ns.route('/<dataset:dataset>/resources/', endpoint='resources')
class ResourcesAPI(API):
    @apiv2.doc('list_resources')
    @apiv2.expect(resources_parser)
    @apiv2.marshal_with(resource_page_fields)
    def get(self, dataset):
        '''Get the given dataset resources, paginated.'''
        args = resources_parser.parse_args()
        page = args['page']
        page_size = args['page_size']
        next_page = f"{url_for('apiv2.resources', dataset=dataset.id, _external=True)}?page={page + 1}&page_size={page_size}"
        previous_page = f"{url_for('apiv2.resources', dataset=dataset.id, _external=True)}?page={page - 1}&page_size={page_size}"
        res = dataset.resources

        if args['type']:
            res = [elem for elem in res if elem['type'] == args['type']]
            next_page += f"&type={args['type']}"
            previous_page += f"&type={args['type']}"

        if args['q']:
            res = [elem for elem in res if args['q'].lower() in elem['title'].lower()]
            next_page += f"&q={args['q']}"
            previous_page += f"&q={args['q']}"

        if page > 1:
            offset = page_size * (page - 1)
        else:
            offset = 0
        paginated_result = res[offset:(page_size + offset if page_size is not None else None)]

        return {
            'data': paginated_result,
            'next_page': next_page if page_size + offset < len(res) else None,
            'page': page,
            'page_size': page_size,
            'previous_page': previous_page if page > 1 else None,
            'total': len(res),
        }


@ns.route('/resources/<uuid:rid>/', endpoint='resource')
class ResourceAPI(API):
    @apiv2.doc('get_resource')
    def get(self, rid):
        dataset = Dataset.objects(resources__id=rid).first()
        if dataset:
            resource = get_by(dataset.resources, 'id', rid)
        else:
            resource = CommunityResource.objects(id=rid).first()
        if not resource:
            apiv2.abort(404, 'Resource does not exist')

        # Manually marshalling to make sure resource.dataset is in the scope.
        # See discussions in https://github.com/opendatateam/udata/pull/2732/files
        return marshal({
            'resource': resource,
            'dataset_id': dataset.id if dataset else None
        }, specific_resource_fields)
