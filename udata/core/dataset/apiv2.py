import logging

from flask import url_for
from flask_restplus.reqparse import RequestParser

from udata.api import apiv2, API, fields

from .models import (
    UPDATE_FREQUENCIES, DEFAULT_FREQUENCY, DEFAULT_LICENSE
)
from .permissions import DatasetEditPermission
from .api_fields import (
    resource_fields,
    badge_fields,
    org_ref_fields,
    user_ref_fields,
    temporal_coverage_fields,
    spatial_coverage_fields,
    DEFAULT_MASK,
)

log = logging.getLogger(__name__)

ns = apiv2.namespace('datasets', 'Dataset related operations')
resources_parser = RequestParser()
resources_parser.add_argument(
    'page', required=True, type=int, default=1, location='args', help='The page to fetch')
resources_parser.add_argument(
    'page_size', required=True, type=int, default=20, location='args',
    help='The page size to fetch')

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
        'href': url_for('apiv2.resources', dataset=o.id, page=1, page_size= 20, _external=True),
        'type': 'GET',
        'total': len(o.resources)
        }, description='Link to the dataset resources'),
    'community_resources': fields.Raw(attribute=lambda o: {
        'rel': 'subsection',
        'href': url_for('api.community_resources', dataset=o.id, page=1, page_size= 20, _external=True),
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
})


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
        if page > 1:
            offset = page_size * (page - 1)
        else:
            offset = 0
        res = dataset.resources[offset:(page_size + offset if page_size is not None else None)]
        return {
            'data': res,
            'next_page': f"{url_for('apiv2.resources', dataset=dataset.id, _external=True)}?page={page + 1}&page_size={page_size}",
            'page': page,
            'page_size': page_size,
            'previous_page': f"{url_for('apiv2.resources', dataset=dataset.id, _external=True)}?page={page - 1}&page_size={page_size}" if page > 1 else None,
            'total': len(dataset.resources),
        }
