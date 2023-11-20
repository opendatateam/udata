from udata.api import api, fields
from udata.core.organization.api_fields import org_ref_fields
from udata.core.user.api_fields import user_ref_fields


contact_point_fields = api.model('ContactPoint', {
    'id': fields.String(description='The contact point\'s identifier', readonly=True),
    'name': fields.String(description='The contact point\'s name', required=True),
    'email': fields.String(description='The contact point\'s email', required=True),
    'organization': fields.Nested(
        org_ref_fields, allow_null=True,
        description='The producer organization'),
    'owner': fields.Nested(
        user_ref_fields, allow_null=True, description='The user information')
})

contact_point_page_fields = api.model('ContactPointPage', fields.pager(contact_point_fields))