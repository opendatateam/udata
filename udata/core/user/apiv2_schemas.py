from marshmallow import Schema, fields
from udata.api.fields import MaURLFor, paginate_schema


class UserRefSchema(Schema):
    first_name = fields.Str(dump_only=True)
    last_name = fields.String(dump_only=True)
    slug = fields.String(required=True)
    page = MaURLFor(endpoint='users.show', mapper=lambda u: {'user': u}, fallback_endpoint='api.user', dump_only=True)
    uri = MaURLFor(endpoint='api.user', mapper=lambda u: {'user': u}, dump_only=True)
    avatar = fields.Url()
    avatar_thumbnail = fields.Url()


from udata.core.organization.apiv2_schemas import OrganizationRefSchema  # noqa


class UserSchema(Schema):
    id = fields.Str(dump_only=True)
    first_name = fields.Str(dump_only=True)
    last_name = fields.String(dump_only=True)
    slug = fields.String(required=True)
    about = fields.String()
    page = MaURLFor(endpoint='users.show', mapper=lambda u: {'user': u}, fallback_endpoint='api.user', dump_only=True)
    uri = MaURLFor(endpoint='api.user', mapper=lambda u: {'user': u}, dump_only=True)
    avatar = fields.Url()
    avatar_thumbnail = fields.Url()
    email = fields.Function(lambda o: o.email if current_user_is_admin_or_self() else None, dump_only=True),
    metrics = fields.Function(lambda obj: obj.get_metrics(), dump_only=True),
    active = fields.Boolean(),
    roles = fields.List(fields.Str()),
    created_at = fields.DateTime('%Y-%m-%dT%H:%M:%S+03:00', dump_only=True)
    organizations = fields.Nested(OrganizationRefSchema, many=True, dump_only=True)


user_pagination_schema = paginate_schema(UserSchema)
