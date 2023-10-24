from udata.api import api, fields


contact_points_fields = api.model('ContactPoint', {
    'id': fields.String(description='The contact point\'s identifier', readonly=True),
    'name': fields.String(description='The contact point\'s name', required=True),
    'email': fields.String(description='The contact point\'s email', required=True)
})

contact_points_page_fields = api.model('ContactPointPage', fields.pager(contact_points_fields))
