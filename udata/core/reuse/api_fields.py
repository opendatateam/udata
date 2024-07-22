from udata.api import api, base_reference, fields
from udata.core.badges.fields import badge_fields
from udata.core.dataset.api_fields import dataset_fields
from udata.core.organization.api_fields import org_ref_fields
from udata.core.user.api_fields import user_ref_fields

from .constants import IMAGE_SIZES, REUSE_TOPICS, REUSE_TYPES

BIGGEST_IMAGE_SIZE = IMAGE_SIZES[0]

reuse_type_fields = api.model('ReuseType', {
    'id': fields.String(description='The reuse type identifier'),
    'label': fields.String(description='The reuse type display name')
})


reuse_suggestion_fields = api.model(
    "ReuseSuggestion",
    {
        "id": fields.String(description="The reuse identifier", readonly=True),
        "title": fields.String(description="The reuse title", readonly=True),
        "slug": fields.String(description="The reuse permalink string", readonly=True),
        "image_url": fields.ImageField(
            size=BIGGEST_IMAGE_SIZE, description="The reuse thumbnail URL", readonly=True
        ),
        "page": fields.UrlFor(
            "reuses.show_redirect",
            lambda o: {"reuse": o["slug"]},
            description="The reuse page URL",
            readonly=True,
            fallback_endpoint="api.reuse",
        ),
    },
)


reuse_topic_fields = api.model(
    "ReuseTopic",
    {
        "id": fields.String(description="The reuse topic identifier"),
        "label": fields.String(description="The reuse topic display name"),
    },
)
