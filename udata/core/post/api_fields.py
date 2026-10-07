from udata.api import api, fields

post_permissions_fields = api.model(
    "PostPermissions",
    {
        "delete": fields.Permission(),
        "edit": fields.Permission(),
    },
)
