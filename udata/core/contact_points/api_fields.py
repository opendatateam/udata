from udata.api import api, fields


contact_points_fields = api.model('Member', {
    'name': fields.String(description='The contact point\'s name'),
    'email': fields.String(description='The contact point\'s email')
})