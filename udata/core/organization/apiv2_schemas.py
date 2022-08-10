from marshmallow import Schema, fields, validate
from .models import ORG_ROLES, DEFAULT_ROLE

from udata.api.fields import MaURLFor, MaNextPageUrl, MaPreviousPageUrl
from udata.core.user.apiv2_schemas import UserSchema


class BadgeSchema(Schema):
    kind = fields.Str(required=True)


class MembersSchema(Schema):
    user = fields.Nested(UserSchema)
    role = fields.Str(validate=validate.OneOf(list(ORG_ROLES)), required=True, dump_default=DEFAULT_ROLE)


class OrganizationSchema(Schema):
    id = fields.Str(dump_only=True)
    name = fields.Str(required=True)
    acronym = fields.Str()
    url = fields.Url()
    slug = fields.Str(required=True, dump_only=True)
    description = fields.Str(required=True)
    created_at = fields.DateTime('%Y-%m-%dT%H:%M:%S+03:00', required=True, dump_only=True)
    last_modified = fields.DateTime('%Y-%m-%dT%H:%M:%S+03:00', required=True, dump_only=True)
    deleted = fields.DateTime('%Y-%m-%dT%H:%M:%S+03:00', dump_only=True)
    metrics = fields.Function(lambda obj: obj.get_metrics())
    logo = fields.Url()
    logo_thumbnail = fields.Url()
    badges = fields.Nested(BadgeSchema, many=True, dump_only=True)
    # members = fields.Nested(UserSchema, many=True, dump_only=True)
    uri = MaURLFor(endpoint='api.organization', mapper=lambda o: {'org': o}, dump_only=True)
    page = MaURLFor(endpoint='organizations.show', mapper=lambda o: {'org': o}, fallback_endpoint='api.organization', dump_only=True)


class OrganizationPaginationSchema(Schema):
    data = fields.List(fields.Nested(OrganizationSchema), attribute="objects")
    page = fields.Int(required=True, min=1)
    page_size = fields.Int(required=True, min=0)
    total = fields.Int(required=True, min=0)
    next_page = MaNextPageUrl()
    previous_page = MaPreviousPageUrl()
