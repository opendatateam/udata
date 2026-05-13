from udata.api import api, fields

source_permissions_fields = api.model(
    "HarvestSourcePermissions",
    {
        "edit": fields.Permission(),
        "delete": fields.Permission(),
        "run": fields.Permission(),
        "preview": fields.Permission(),
        "validate": fields.Permission(),
        "schedule": fields.Permission(),
    },
)
