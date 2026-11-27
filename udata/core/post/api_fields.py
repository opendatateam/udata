from udata.api import api, fields

post_permissions_fields = api.model(
    "PostPermissions",
    {
        "delete": fields.Permission(),
        "edit": fields.Permission(),
    },
)

post_ancestor_fields = api.model(
    "PostAncestor",
    {
        "id": fields.String(description="The post identifier", readonly=True),
        "name": fields.String(description="The post name", readonly=True),
        "page": fields.String(
            attribute=lambda post: post.self_web_url(),
            description="The post web page URL",
            readonly=True,
        ),
    },
)
