import logging

from flask import url_for, request, abort, jsonify
from werkzeug.routing import BuildError

from udata import search
from udata.app import Blueprint
from udata.utils import multi_to_dict, get_by

from marshmallow import Schema, fields, validate
from webargs import fields as arg_field, validate as arg_validate
from webargs.flaskparser import use_args


from .models import (
    Dataset, UPDATE_FREQUENCIES, DEFAULT_FREQUENCY, DEFAULT_LICENSE, CommunityResource,
    RESOURCE_TYPES, RESOURCE_FILETYPES, CHECKSUM_TYPES, DEFAULT_CHECKSUM_TYPE
)
from .permissions import DatasetEditPermission

DEFAULT_PAGE_SIZE = 50
DEFAULT_SORTING = '-created_at'


log = logging.getLogger(__name__)
ns = Blueprint('datasets', __name__)


class BadgeSchema(Schema):
    kind = fields.Str(required=True)


class OrganizationSchema(Schema):
    name = fields.Str(dump_only=True)
    acronym = fields.Str()
    # uri = fields.Url('api.organization', lambda o: {'org': o}, readonly=True)
    slug = fields.Str(required=True)
    # page = fields.Url('organizations.show', lambda o: {'org': o}, readonly=True, fallback_endpoint='api.organization')
    logo = fields.Url()
    logo_thumbnail = fields.Url()
    badges = fields.Nested(BadgeSchema, many=True, dump_only=True)


class UserSchema(Schema):
    first_name = fields.Str(readonly=True)
    last_name = fields.String(readonly=True)
    slug = fields.String(required=True)
    # page = fields.Url('users.show', lambda u: {'user': u}, readonly=True, fallback_endpoint='api.user')
    # uri = fields.Url('api.user', lambda o: {'user': o}, required=True)
    # avatar = fields.Url(original=True)
    # avatar_thumbnail = fields.Url(attribute='avatar', size=BIGGEST_AVATAR_SIZE)


class TemporalCoverageSchema(Schema):
    start = fields.DateTime('%Y-%m-%dT%H:%M:%S+03:00', required=True)
    end = fields.DateTime('%Y-%m-%dT%H:%M:%S+03:00', required=True)


class GeoJsonSchema(Schema):
    type = fields.Str(required=True)
    coordinates = fields.List(fields.Raw(), required=True)


class SpatialCoverageSchema(Schema):
    geom = fields.Nested(GeoJsonSchema)
    zones = fields.List(fields.Str)
    granularity = fields.Str(default='other')


class DatasetSchema(Schema):
    id = fields.Str(dump_only=True)
    title = fields.Str(required=True)
    acronym = fields.Str()
    slug = fields.Str(required=True)
    description = fields.Str(required=True)
    created_at = fields.DateTime('%Y-%m-%dT%H:%M:%S+03:00', required=True)
    last_modified = fields.DateTime('%Y-%m-%dT%H:%M:%S+03:00', required=True)
    deleted = fields.DateTime('%Y-%m-%dT%H:%M:%S+03:00')
    archived = fields.DateTime('%Y-%m-%dT%H:%M:%S+03:00')
    featured = fields.Boolean(description='Is the dataset featured')
    private = fields.Boolean()
    tags = fields.List(fields.Str)
    badges = fields.Nested(BadgeSchema, many=True, dump_only=True)
    resources = fields.Function(lambda obj: {
        'rel': 'subsection',
        'href': url_for('api.resources', dataset=obj.id, page=1, page_size=DEFAULT_PAGE_SIZE, _external=True),
        'type': 'GET',
        'total': len(obj.resources)
        })
    community_resources = fields.Function(lambda obj: {
        'rel': 'subsection',
        'href': url_for('api.community_resources', dataset=obj.id, page=1, page_size=DEFAULT_PAGE_SIZE, _external=True),
        'type': 'GET',
        'total': len(obj.community_resources)
        })
    frequency = fields.Str(required=True, dump_default=DEFAULT_FREQUENCY, validate=validate.OneOf(UPDATE_FREQUENCIES))
    frequency_date = fields.DateTime('%Y-%m-%dT%H:%M:%S+03:00')
    extras = fields.Dict()
    metrics = fields.Function(lambda obj: obj.get_metrics())
    organization = fields.Nested(OrganizationSchema)
    owner = fields.Nested(UserSchema)
    temporal_coverage = fields.Nested(TemporalCoverageSchema)
    spatial = fields.Nested(SpatialCoverageSchema)
    license = fields.Method("dataset_license")
    uri = fields.Method("dataset_uri")
    page = fields.Method("dataset_page")
    quality = fields.Dict(dump_only=True)
    last_update = fields.DateTime('%Y-%m-%dT%H:%M:%S+03:00', required=True)

    def dataset_license(self, obj):
        if obj.license:
            return obj.license.id
        else:
            return DEFAULT_LICENSE['id']

    def dataset_uri(self, obj):
        return url_for('api.dataset', dataset=obj, _external=True)

    def dataset_page(self, obj):
        try:
            return url_for('datasets.show', dataset=obj, _external=True)
        except BuildError:
            return url_for('api.dataset', dataset=obj, _external=True)


class ChecksumSchema(Schema):
    type = fields.Str(default=DEFAULT_CHECKSUM_TYPE, validate=validate.OneOf(CHECKSUM_TYPES))
    value = fields.Str(required=True)


class ResourceSchema(Schema):
    id = fields.Str(readonly=True)
    title = fields.Str(required=True)
    description = fields.Str()
    filetype = fields.Str(required=True, validate=validate.OneOf(RESOURCE_FILETYPES))
    type = fields.Str(required=True, validate=validate.OneOf(RESOURCE_TYPES))
    format = fields.Str(required=True)
    url = fields.Str(required=True)
    latest = fields.Str(readonly=True)
    checksum = fields.Nested(ChecksumSchema)
    filesize = fields.Integer()
    mime = fields.Str()
    created_at = fields.DateTime(dump_only=True)
    published = fields.DateTime()
    last_modified = fields.DateTime(dump_only=True)
    metrics = fields.Raw(dump_only=True)
    extras = fields.Raw()
    preview_url = fields.Str(dump_only=True)
    schema = fields.Raw(dump_only=True)


class DatasetPageSchema(Schema):
    data = fields.Nested(DatasetSchema, many=True)
    next_page = fields.Str()
    previous_page = fields.Str()
    page = fields.Integer(required=True)
    page_size = fields.Integer(required=True)
    total = fields.Integer()


class ResourcePageSchema(Schema):
    data = fields.Nested(ResourceSchema, many=True)
    next_page = fields.Str()
    previous_page = fields.Str()
    page = fields.Integer(required=True, default=1)
    page_size = fields.Integer(required=True, default=20)
    total = fields.Integer()


class SpecificResourceSchema(Schema):
    resource = fields.Nested(ResourceSchema)
    dataset_id = fields.Str()


SORTS = [
    'created',
    'reuses',
    'followers',
    'views',
    '-created',
    '-reuses',
    '-followers',
    '-views'
]


resources_parser_args = {
    'page': arg_field.Int(missing=1),
    'page_size': arg_field.Int(missing=20),
    'type': arg_field.Str(),
    'q': arg_field.Str()
}


dataset_search_args = {
    "q": arg_field.Str(),
    'tag': arg_field.Str(),
    'badge': arg_field.Str(),
    'organization': arg_field.Str(),
    'owner': arg_field.Str(),
    'license': arg_field.Str(),
    'geozone': arg_field.Str(),
    'granularity': arg_field.Str(),
    'format': arg_field.Str(),
    'schema': arg_field.Str(),
    'temporal_coverage': arg_field.Str(),
    'featured': arg_field.Bool(),
    'sort': arg_field.Str(validate=arg_validate.OneOf(SORTS)),
    'page': arg_field.Int(missing=1),
    'page_size': arg_field.Int(missing=20)
}


@ns.route('/search/', endpoint='dataset_search', methods=['GET'])
@use_args(dataset_search_args, location="query")
def get_dataset_search(args):
    '''List or search all datasets'''
    try:
        result = search.query(Dataset, **multi_to_dict(request.args))
        return jsonify(DatasetSchema().dump(result, many=True))
    except NotImplementedError:
        abort(501, 'Search endpoint not enabled')
    except RuntimeError:
        abort(500, 'Internal search service error')


@ns.route('/<dataset:dataset>/', endpoint='dataset', methods=['GET'])
def get_specific_dataset_by_id(dataset):
    '''Get a dataset given its identifier'''
    if dataset.deleted and not DatasetEditPermission(dataset).can():
        abort(410, 'Dataset has been deleted')
    return jsonify(DatasetSchema().dump(dataset))


@ns.route('/<dataset:dataset>/resources/', endpoint='resources', methods=['GET'])
@use_args(resources_parser_args, location="query")
def get_resources_paginated(args, dataset):
    '''Get the given dataset resources, paginated.'''
    # args = parser.parse(resources_parser_args, request)
    page = args['page']
    page_size = args['page_size']
    next_page = f"{url_for('apiv2.datasets.resources', dataset=dataset.id, _external=True)}?page={page + 1}&page_size={page_size}"
    previous_page = f"{url_for('apiv2.datasets.resources', dataset=dataset.id, _external=True)}?page={page - 1}&page_size={page_size}"
    res = dataset.resources

    if args.get('type'):
        res = [elem for elem in res if elem['type'] == args['type']]
        next_page += f"&type={args['type']}"
        previous_page += f"&type={args['type']}"

    if args.get('q'):
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


@ns.route('/resources/<uuid:rid>/', endpoint='resource', methods=['GET'])
def get_specific_resource_by_rid(rid):
    dataset = Dataset.objects(resources__id=rid).first()
    if dataset:
        resource = get_by(dataset.resources, 'id', rid)
    else:
        resource = CommunityResource.objects(id=rid).first()
    if not resource:
        abort(404, 'Resource does not exist')

    return {
        'resource': ResourceSchema().dump(resource),
        'dataset_id': dataset.id if dataset else None
    }
