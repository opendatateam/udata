from udata.api import api, fields

from .constants import IMAGE_SIZES

BIGGEST_IMAGE_SIZE = IMAGE_SIZES[0]

reuse_permissions_fields = api.model(
    "ReusePermissions",
    {
        "delete": fields.Permission(),
        "edit": fields.Permission(),
    },
)

reuse_type_fields = api.model(
    "ReuseType",
    {
        "id": fields.String(description="The reuse type identifier"),
        "label": fields.String(description="The reuse type display name"),
    },
)


reuse_suggestion_fields = api.model(
    "ReuseSuggestion",
    {
        "id": fields.String(description="The reuse identifier", readonly=True),
        "title": fields.String(description="The reuse title", readonly=True),
        "slug": fields.String(description="The reuse permalink string", readonly=True),
        "image_url": fields.ImageField(
            size=BIGGEST_IMAGE_SIZE, description="The reuse thumbnail URL", readonly=True
        ),
        "page": fields.String(description="The reuse web page URL", readonly=True),
    },
)


reuse_topic_fields = api.model(
    "ReuseTopic",
    {
        "id": fields.String(description="The reuse topic identifier"),
        "label": fields.String(description="The reuse topic display name"),
    },
)
