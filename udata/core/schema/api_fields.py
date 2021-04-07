from udata.api import api, fields, base_reference


schema_ref_fields = api.inherit('SchemaReference', {
    'name': fields.String(description='The schema name'),
    'version': fields.String(description='The schema version'),
})
