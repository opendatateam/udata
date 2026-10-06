from udata.api import api, fields

page_permissions_fields = api.model(
    "PagePermissions",
    {
        "delete": fields.Permission(),
        "edit": fields.Permission(),
    },
)
