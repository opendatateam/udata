from udata.api import api, fields
from udata.core.organization.models import Organization
from udata.core.user.models import User, _visible_email

from .constants import BIGGEST_AVATAR_SIZE

# `User.organizations` is a reverse query (`cached_property`), so it cannot be
# wrapped with `field()` on the model — post-decorate the generated read fields
# here to expose it as a list of org references.
User.__read_fields__["organizations"] = fields.List(
    fields.Nested(Organization.__ref_fields__),
    attribute=lambda u: list(u.organizations),
    description="The organizations the user belongs to",
    readonly=True,
)

me_metrics_fields = api.model(
    "MyMetrics",
    {
        "id": fields.String(description="The user identifier", required=True),
        "resources_availability": fields.Float(
            description="The user's resources availability percentage", readonly=True
        ),
        "datasets_org_count": fields.Integer(
            description="The user's orgs datasets number", readonly=True
        ),
        "followers_org_count": fields.Integer(
            description="The user's orgs followers number", readonly=True
        ),
        "datasets_count": fields.Integer(description="The user's datasets number", readonly=True),
        "followers_count": fields.Integer(description="The user's followers number", readonly=True),
    },
)

user_suggestion_fields = api.model(
    "UserSuggestion",
    {
        "id": fields.String(description="The user identifier", readonly=True),
        "first_name": fields.String(description="The user first name", readonly=True),
        "last_name": fields.String(description="The user last name", readonly=True),
        "avatar_url": fields.ImageField(
            attribute="avatar",
            size=BIGGEST_AVATAR_SIZE,
            description="The user avatar URL",
            readonly=True,
        ),
        "email": fields.Raw(
            attribute=lambda o: _visible_email(o),
            description="The user email (only the domain for non-admin user)",
            readonly=True,
        ),
        "slug": fields.String(description="The user permalink string", readonly=True),
    },
)

notifications_fields = api.model(
    "Notification",
    {
        "type": fields.String(description="The notification type", readonly=True),
        "created_on": fields.ISODateTime(
            description="The notification creation datetime", readonly=True
        ),
        "details": fields.Raw(
            description="Key-Value details depending on notification type", readonly=True
        ),
    },
)


user_role_fields = api.model(
    "UserRole",
    {
        "name": fields.String(description="The role name", readonly=True),
    },
)
