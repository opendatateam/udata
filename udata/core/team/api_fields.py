from udata.api import api, fields
from udata.core.user.api_fields import user_fields


team_fields = api.model('Team', {
    'id': fields.String(
        description='The team identifier', required=True),
    'name': fields.String(description='The team name', required=True),
    'slug': fields.String(
        description='The team string used as permalink',
        required=True),
    'description': fields.Markdown(
        description='The team description in Markdown', required=True),
    'members': fields.List(
        fields.Nested(user_fields, description='The team members'))
})
