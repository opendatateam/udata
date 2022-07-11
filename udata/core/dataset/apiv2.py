# import logging
#
# from flask import url_for, request, abort, jsonify
# from werkzeug.routing import BuildError
# from mongoengine.errors import DoesNotExist
#
# from udata import search
# from udata.app import Blueprint
# from udata.utils import multi_to_dict, get_by
#
# from marshmallow import Schema, fields, validate
#
#
# from .models import (
#     Dataset, UPDATE_FREQUENCIES, DEFAULT_FREQUENCY, DEFAULT_LICENSE, CommunityResource,
#     RESOURCE_TYPES, RESOURCE_FILETYPES, CHECKSUM_TYPES, DEFAULT_CHECKSUM_TYPE
# )
# from .permissions import DatasetEditPermission
# from .search import DatasetSearch
#
# DEFAULT_PAGE_SIZE = 50
# DEFAULT_SORTING = '-created_at'
#
#
# log = logging.getLogger(__name__)
# ns = Blueprint('datasets', __name__, url_prefix='/datasets')
#
# #from webargs import fields, validate
#
# # user_args = {
# #     "q": fields.Str(),
# #     "sort": fields.Str(),
# #     "page": fields.Int(missing=1),
# #     "page_size": fields.Int(missing=20)
# # }
#
#
# class UrlFor(fields.Field):
#
#     def _serialize(self, value, attr, obj, **kwargs):
#         print(obj)
#
#     def _deserialize(self, value, attr, data, **kwargs):
#         print(data)
#
#
# class BadgeSchema(Schema):
#     kind = fields.Str(required=True)
#
#
# class OrganizationSchema(Schema):
#     name = fields.Str(dump_only=True)
#     acronym = fields.Str()
#     # uri = fields.Url('api.organization', lambda o: {'org': o}, readonly=True)
#     slug = fields.Str(required=True)
#     # page = fields.Url('organizations.show', lambda o: {'org': o}, readonly=True, fallback_endpoint='api.organization')
#     logo = fields.Url()
#     logo_thumbnail = fields.Url()
#     badges = fields.Nested(BadgeSchema, many=True, dump_only=True)
#
#
# class UserSchema(Schema):
#     first_name = fields.Str(readonly=True)
#     last_name = fields.String(readonly=True)
#     slug = fields.String(required=True)
#     # page = fields.Url('users.show', lambda u: {'user': u}, readonly=True, fallback_endpoint='api.user')
#     # uri = fields.Url('api.user', lambda o: {'user': o}, required=True)
#     # avatar = fields.Url(original=True)
#     # avatar_thumbnail = fields.Url(attribute='avatar', size=BIGGEST_AVATAR_SIZE)
#
#
# class TemporalCoverageSchema(Schema):
#     start = fields.DateTime('%Y-%m-%dT%H:%M:%S+03:00', required=True)
#     end = fields.DateTime('%Y-%m-%dT%H:%M:%S+03:00', required=True)
#
#
# class GeoJsonSchema(Schema):
#     type = fields.Str(required=True)
#     coordinates = fields.List(fields.Raw(), required=True)
#
#
# class SpatialCoverageSchema(Schema):
#     geom = fields.Nested(GeoJsonSchema)
#     zones = fields.List(fields.Str)
#     granularity = fields.Str(default='other')
#
#
# class DatasetSchema(Schema):
#     id = fields.Str(dump_only=True)
#     title = fields.Str(required=True)
#     acronym = fields.Str()
#     slug = fields.Str(required=True)
#     description = fields.Str(required=True)
#     created_at = fields.DateTime('%Y-%m-%dT%H:%M:%S+03:00', required=True)
#     last_modified = fields.DateTime('%Y-%m-%dT%H:%M:%S+03:00', required=True)
#     deleted = fields.DateTime('%Y-%m-%dT%H:%M:%S+03:00')
#     archived = fields.DateTime('%Y-%m-%dT%H:%M:%S+03:00')
#     featured = fields.Boolean(description='Is the dataset featured')
#     private = fields.Boolean()
#     tags = fields.List(fields.Str)
#     badges = fields.Nested(BadgeSchema, many=True, dump_only=True)
#     resources = fields.Function(lambda obj: {
#         'rel': 'subsection',
#         'href': url_for('api.resources', dataset=obj.id, page=1, page_size=DEFAULT_PAGE_SIZE, _external=True),
#         'type': 'GET',
#         'total': len(obj.resources)
#         })
#     community_resources = fields.Function(lambda obj: {
#         'rel': 'subsection',
#         'href': url_for('api.community_resources', dataset=obj.id, page=1, page_size=DEFAULT_PAGE_SIZE, _external=True),
#         'type': 'GET',
#         'total': len(obj.community_resources)
#         })
#     frequency = fields.Str(required=True, dump_default=DEFAULT_FREQUENCY, validate=validate.OneOf(UPDATE_FREQUENCIES))
#     frequency_date = fields.DateTime('%Y-%m-%dT%H:%M:%S+03:00')
#     extras = fields.Dict()
#     metrics = fields.Function(lambda obj: obj.get_metrics())
#     organization = fields.Nested(OrganizationSchema)
#     owner = fields.Nested(UserSchema)
#     temporal_coverage = fields.Nested(TemporalCoverageSchema)
#     spatial = fields.Nested(SpatialCoverageSchema)
#     license = fields.Method("dataset_license")
#     uri = fields.Method("dataset_uri")
#     page = fields.Method("dataset_page")
#     quality = fields.Dict(dump_only=True)
#     last_update = fields.DateTime('%Y-%m-%dT%H:%M:%S+03:00', required=True)
#
#     def dataset_license(self, obj):
#         try:
#             return obj.license.id
#         except DoesNotExist:
#             return DEFAULT_LICENSE['id']
#
#     def dataset_uri(self, obj):
#         return url_for('api.dataset', dataset=obj, _external=True)
#
#     def dataset_page(self, obj):
#         try:
#             return url_for('datasets.show', dataset=obj, _external=True)
#         except BuildError:
#             return url_for('api.dataset', dataset=obj, _external=True)
#
#
# class ChecksumSchema(Schema):
#     type = fields.Str(default=DEFAULT_CHECKSUM_TYPE, validate=validate.OneOf(CHECKSUM_TYPES))
#     value = fields.Str(required=True)
#
#
# class ResourceSchema(Schema):
#     id = fields.Str(readonly=True)
#     title = fields.Str(required=True)
#     description = fields.Str()
#     filetype = fields.Str(required=True, validate=validate.OneOf(RESOURCE_FILETYPES))
#     type = fields.Str(required=True, validate=validate.OneOf(RESOURCE_TYPES))
#     format = fields.Str(required=True)
#     url = fields.Str(required=True)
#     latest = fields.Str(readonly=True)
#     checksum = fields.Nested(ChecksumSchema)
#     filesize = fields.Integer()
#     mime = fields.Str()
#     created_at = fields.DateTime(dump_only=True)
#     published = fields.DateTime()
#     last_modified = fields.DateTime(dump_only=True)
#     metrics = fields.Raw(dump_only=True)
#     extras = fields.Raw()
#     preview_url = fields.Str(dump_only=True)
#     schema = fields.Raw(dump_only=True)
#
#
# class DatasetPageSchema(Schema):
#     data = fields.Nested(DatasetSchema, many=True)
#     next_page = fields.Str()
#     previous_page = fields.Str()
#     page = fields.Integer(required=True)
#     page_size = fields.Integer(required=True)
#     total = fields.Integer()
#
#
# class ResourcePageSchema(Schema):
#     data = fields.Nested(ResourceSchema, many=True)
#     next_page = fields.Str()
#     previous_page = fields.Str()
#     page = fields.Integer(required=True, default=1)
#     page_size = fields.Integer(required=True, default=20)
#     total = fields.Integer()
#
#
# class SpecificResourceSchema(Schema):
#     resource = fields.Nested(ResourceSchema)
#     dataset_id = fields.Str()
#
#
# # search_parser = DatasetSearch.as_request_parser()
# # resources_parser = apiv2.parser()
# # resources_parser.add_argument(
# #     'page', type=int, default=1, location='args', help='The page to fetch')
# # resources_parser.add_argument(
# #     'page_size', type=int, default=DEFAULT_PAGE_SIZE, location='args',
# #     help='The page size to fetch')
# # resources_parser.add_argument(
# #     'type', type=str, location='args',
# #     help='The type of resources to fetch')
# # resources_parser.add_argument(
# #     'q', type=str, location='args',
# #     help='query str to search through resources titles')
#
#
# # @apiv2.expect(search_parser)
# # @apiv2.marshal_with(dataset_page_fields)
# @ns.route('/search/', endpoint='dataset_search', methods=['GET'])
# def get_dataset_search():
#     '''List or search all datasets'''
#     # search_parser.parse_args()
#     try:
#         bob = search.query(Dataset, **multi_to_dict(request.args))
#         return jsonify(DatasetSchema().dump(bob, many=True))
#     except NotImplementedError:
#         abort(501, 'Search endpoint not enabled')
#     except RuntimeError:
#         abort(500, 'Internal search service error')
#
#
# @ns.route('/<dataset:dataset>/', endpoint='dataset', methods=['GET'])
# def get_specific_dataset_by_id(dataset):
#     '''Get a dataset given its identifier'''
#     if dataset.deleted and not DatasetEditPermission(dataset).can():
#         abort(410, 'Dataset has been deleted')
#     return jsonify(DatasetSchema().dump(dataset))
#
#
# # @ns.route('/<dataset:dataset>/resources/', endpoint='resources')
# # class ResourcesAPI(API):
# #     @apiv2.doc('list_resources')
# #     @apiv2.expect(resources_parser)
# #     @apiv2.marshal_with(resource_page_fields)
# #     def get(self, dataset):
# #         '''Get the given dataset resources, paginated.'''
# #         args = resources_parser.parse_args()
# #         page = args['page']
# #         page_size = args['page_size']
# #         next_page = f"{url_for('apiv2.resources', dataset=dataset.id, _external=True)}?page={page + 1}&page_size={page_size}"
# #         previous_page = f"{url_for('apiv2.resources', dataset=dataset.id, _external=True)}?page={page - 1}&page_size={page_size}"
# #         res = dataset.resources
# #
# #         if args['type']:
# #             res = [elem for elem in res if elem['type'] == args['type']]
# #             next_page += f"&type={args['type']}"
# #             previous_page += f"&type={args['type']}"
# #
# #         if args['q']:
# #             res = [elem for elem in res if args['q'].lower() in elem['title'].lower()]
# #             next_page += f"&q={args['q']}"
# #             previous_page += f"&q={args['q']}"
# #
# #         if page > 1:
# #             offset = page_size * (page - 1)
# #         else:
# #             offset = 0
# #         paginated_result = res[offset:(page_size + offset if page_size is not None else None)]
# #
# #         return {
# #             'data': paginated_result,
# #             'next_page': next_page if page_size + offset < len(res) else None,
# #             'page': page,
# #             'page_size': page_size,
# #             'previous_page': previous_page if page > 1 else None,
# #             'total': len(res),
# #         }
#
#
# @ns.route('/resources/<uuid:rid>/', endpoint='resource', methods=['GET'])
# def get_specific_resource_by_rid(rid):
#     dataset = Dataset.objects(resources__id=rid).first()
#     if dataset:
#         resource = get_by(dataset.resources, 'id', rid)
#     else:
#         resource = CommunityResource.objects(id=rid).first()
#     if not resource:
#         abort(404, 'Resource does not exist')
#
#     return {
#         'resource': ResourceSchema().dump(resource),
#         'dataset_id': dataset.id if dataset else None
#     }
