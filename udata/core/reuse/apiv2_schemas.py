from marshmallow import Schema, fields, validate
from udata.api.fields import MaURLFor, MaNextPageUrl, MaPreviousPageUrl
from udata.core.dataset.apiv2_schemas import DatasetSchema
from udata.core.user.apiv2_schemas import UserSchema
from udata.core.organization.apiv2_schemas import OrganizationSchema, BadgeSchema
from .models import REUSE_TYPES, REUSE_TOPICS


class ReuseSchema(Schema):
    id = fields.Str(dump_only=True)
    title = fields.Str(required=True)
    slug = fields.Str(required=True, dump_only=True)
    description = fields.Str(required=True)
    url = fields.Url()
    type = fields.Str(required=True, validate=validate.OneOf(REUSE_TYPES))
    topic = fields.Str(required=True, validate=validate.OneOf(REUSE_TOPICS))
    featured = fields.Boolean()
    private = fields.Boolean()
    tags = fields.List(fields.Str)
    badges = fields.Nested(BadgeSchema, many=True, dump_only=True)
    created_at = fields.DateTime('%Y-%m-%dT%H:%M:%S+03:00', required=True, dump_only=True)
    last_modified = fields.DateTime('%Y-%m-%dT%H:%M:%S+03:00', required=True, dump_only=True)
    deleted = fields.DateTime('%Y-%m-%dT%H:%M:%S+03:00', dump_only=True)
    metrics = fields.Function(lambda obj: obj.get_metrics())
    owner = fields.Nested(UserSchema, dump_only=True)
    organization = fields.Nested(OrganizationSchema, dump_only=True)
    datasets = fields.List(fields.Nested(DatasetSchema))
    image = fields.Url()
    image_thumbnail = fields.Url()
    uri = MaURLFor(endpoint='api.reuse', mapper=lambda o: {'reuse': o}, dump_only=True)
    page = MaURLFor(endpoint='reuses.show', mapper=lambda o: {'reuse': o}, fallback_endpoint='api.reuse', dump_only=True)


class ReusePaginationSchema(Schema):
    data = fields.List(fields.Nested(ReuseSchema), attribute="objects")
    page = fields.Int(required=True, min=1)
    page_size = fields.Int(required=True, min=0)
    total = fields.Int(required=True, min=0)
    next_page = MaNextPageUrl()
    previous_page = MaPreviousPageUrl()
