from marshmallow import Schema, fields, validate
from udata.api import BaseReferenceSchema
from udata.api.fields import MarshURLFor, MarshImageField, PaginationSchema
from udata.core.badges.api import BadgeSchema
from udata.core.dataset.apiv2_schemas import DatasetRefSchema
from udata.core.user.apiv2_schemas import UserRefSchema
from udata.core.organization.apiv2_schemas import OrganizationRefSchema
from .models import REUSE_TOPICS, REUSE_TYPES, IMAGE_SIZES

BIGGEST_IMAGE_SIZE = IMAGE_SIZES[0]


class ReuseRefSchema(BaseReferenceSchema):
    title = fields.Str(required=True)
    image = MarshImageField(dump_only=True)
    image_thumbnail = MarshImageField(dump_only=True, attribute='image', size=BIGGEST_IMAGE_SIZE)
    uri = MarshURLFor(endpoint='api.reuse', mapper=lambda o: {'reuse': o}, dump_only=True)
    page = MarshURLFor(endpoint='reuses.show', mapper=lambda o: {'reuse': o}, fallback_endpoint='api.reuse', dump_only=True)


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
    created_at = fields.DateTime('%Y-%m-%dT%H:%M:%S+01:00', required=True, dump_only=True)
    last_modified = fields.DateTime('%Y-%m-%dT%H:%M:%S+01:00', required=True, dump_only=True)
    deleted = fields.DateTime('%Y-%m-%dT%H:%M:%S+01:00', dump_only=True)
    metrics = fields.Function(lambda obj: obj.get_metrics())
    owner = fields.Nested(UserRefSchema, dump_only=True)
    organization = fields.Nested(OrganizationRefSchema, dump_only=True)
    datasets = fields.List(fields.Nested(DatasetRefSchema))
    image = MarshImageField(dump_only=True)
    image_thumbnail = MarshImageField(dump_only=True, attribute='image', size=BIGGEST_IMAGE_SIZE)
    uri = MarshURLFor(endpoint='api.reuse', mapper=lambda o: {'reuse': o}, dump_only=True)
    page = MarshURLFor(endpoint='reuses.show', mapper=lambda o: {'reuse': o}, fallback_endpoint='api.reuse', dump_only=True)


class ReusePaginationSchema(PaginationSchema):
    data = fields.List(fields.Nested(ReuseSchema), attribute="objects")
