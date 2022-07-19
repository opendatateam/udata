from marshmallow import Schema, fields
from udata.api.fields import MaURLFor


class UserSchema(Schema):
    first_name = fields.Str(dump_only=True)
    last_name = fields.String(dump_only=True)
    slug = fields.String(required=True)
    page = MaURLFor(endpoint='users.show', mapper=lambda u: {'user': u}, fallback_endpoint='api.user', dump_only=True)
    uri = MaURLFor(endpoint='api.user', mapper=lambda u: {'user': u}, dump_only=True)
    avatar = fields.Url()
    avatar_thumbnail = fields.Url()
