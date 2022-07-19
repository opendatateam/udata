from flask import url_for
from marshmallow import Schema, fields, validate

from udata.api.fields import MaURLFor
from udata.core.organization.apiv2_schemas import OrganizationSchema
from udata.core.user.apiv2_schemas import UserSchema

from .models import (
    UPDATE_FREQUENCIES, DEFAULT_FREQUENCY, DEFAULT_LICENSE,
    RESOURCE_TYPES, RESOURCE_FILETYPES, CHECKSUM_TYPES, DEFAULT_CHECKSUM_TYPE
)


DEFAULT_PAGE_SIZE = 50


class BadgeSchema(Schema):
    kind = fields.Str(required=True)


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
    uri = MaURLFor(endpoint='api.dataset', mapper=lambda o: {'dataset': o}, dump_only=True)
    page = MaURLFor(endpoint='datasets.show', mapper=lambda o: {'dataset': o}, fallback_endpoint='api.dataset', dump_only=True)
    acronym = fields.Str()
    slug = fields.Str(required=True, dump_only=True)
    description = fields.Str(required=True)
    created_at = fields.DateTime('%Y-%m-%dT%H:%M:%S+03:00', required=True)
    last_modified = fields.DateTime('%Y-%m-%dT%H:%M:%S+03:00', required=True)
    deleted = fields.DateTime('%Y-%m-%dT%H:%M:%S+03:00')
    archived = fields.DateTime('%Y-%m-%dT%H:%M:%S+03:00')
    featured = fields.Boolean()
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
    quality = fields.Dict(dump_only=True)
    last_update = fields.DateTime('%Y-%m-%dT%H:%M:%S+03:00', required=True)

    def dataset_license(self, obj):
        if obj.license:
            return obj.license.id
        else:
            return DEFAULT_LICENSE['id']


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
