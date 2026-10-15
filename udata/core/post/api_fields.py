from udata.api import api, fields

post_ancestor_fields = api.model(
    "PostAncestor",
    {
        "id": fields.String(description="The post identifier", readonly=True),
        "name": fields.String(description="The post name", readonly=True),
        "path": fields.String(description="The page path", readonly=True),
    },
)
