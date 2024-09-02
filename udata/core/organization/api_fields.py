from flask import request

from udata.api import api, base_reference, fields
from udata.core.badges.fields import badge_fields
from udata.core.organization.permissions import OrganizationPrivatePermission

from .constants import BIGGEST_LOGO_SIZE, DEFAULT_ROLE, MEMBERSHIP_STATUS, ORG_ROLES

org_ref_fields = api.inherit(
    "OrganizationReference",
    base_reference,
    {
        "name": fields.String(description="The organization name", readonly=True),
        "acronym": fields.String(description="The organization acronym"),
        "uri": fields.UrlFor(
            "api.organization",
            lambda o: {"org": o},
            description="The organization API URI",
            readonly=True,
        ),
        "slug": fields.String(
            description="The organization string used as permalink", required=True
        ),
        "page": fields.UrlFor(
            "organizations.show",
            lambda o: {"org": o},
            description="The organization web page URL",
            readonly=True,
            fallback_endpoint="api.organization",
        ),
        "logo": fields.ImageField(original=True, description="The organization logo URL"),
        "logo_thumbnail": fields.ImageField(
            attribute="logo",
            size=BIGGEST_LOGO_SIZE,
            description="The organization logo thumbnail URL. This is the square "
            "({0}x{0}) and cropped version.".format(BIGGEST_LOGO_SIZE),
        ),
        "badges": fields.List(
            fields.Nested(badge_fields), description="The organization badges", readonly=True
        ),
    },
)

# This import is not at the top of the file to avoid circular imports
from udata.core.user.api_fields import user_ref_fields  # noqa


def check_can_access_user_private_info():
    # This endpoint is secure, only organization member has access.
    if request.endpoint == "api.request_membership":
        return True

    if request.endpoint != "api.organization":
        return False

    org = request.view_args.get("org")
    if org is None:
        return False

    return OrganizationPrivatePermission(org).can()


member_user_with_email_fields = api.inherit(
    "MemberUserWithEmail",
    user_ref_fields,
    {
        "email": fields.Raw(
            attribute=lambda o: o.email if check_can_access_user_private_info() else None,
            description="The user email (only present on show organization endpoint if the current user is member of the organization: admin or editor)",
            readonly=True,
        ),
        "last_login_at": fields.Raw(
            attribute=lambda o: o.last_login_at if check_can_access_user_private_info() else None,
            description="The user last connection date (only present on show organization endpoint if the current user is member of the organization: admin or editor)",
            readonly=True,
        ),
    },
)

request_fields = api.model(
    "MembershipRequest",
    {
        "id": fields.String(readonly=True),
        "user": fields.Nested(member_user_with_email_fields),
        "created": fields.ISODateTime(description="The request creation date", readonly=True),
        "status": fields.String(
            description="The current request status", required=True, enum=list(MEMBERSHIP_STATUS)
        ),
        "comment": fields.String(description="A request comment from the user", required=True),
    },
)

member_fields = api.model(
    "Member",
    {
        "user": fields.Nested(member_user_with_email_fields),
        "role": fields.String(
            description="The member role in the organization",
            required=True,
            enum=list(ORG_ROLES),
            default=DEFAULT_ROLE,
        ),
        "since": fields.ISODateTime(
            description="The date the user joined the organization", readonly=True
        ),
    },
)

org_fields = api.model(
    "Organization",
    {
        "id": fields.String(description="The organization identifier", required=True),
        "name": fields.String(description="The organization name", required=True),
        "acronym": fields.String(description="The organization acronym"),
        "url": fields.String(description="The organization website URL"),
        "slug": fields.String(
            description="The organization string used as permalink", required=True
        ),
        "description": fields.Markdown(
            description="The organization description in Markdown", required=True
        ),
        "business_number_id": fields.String(
            description="The organization's business identification number."
        ),
        "created_at": fields.ISODateTime(
            description="The organization creation date", readonly=True
        ),
        "last_modified": fields.ISODateTime(
            description="The organization last modification date", readonly=True
        ),
        "deleted": fields.ISODateTime(
            description="The organization deletion date if deleted", readonly=True
        ),
        "metrics": fields.Raw(
            attribute=lambda o: o.get_metrics(),
            description="The organization metrics",
            readonly=True,
        ),
        "uri": fields.UrlFor(
            "api.organization",
            lambda o: {"org": o},
            description="The organization API URI",
            readonly=True,
        ),
        "page": fields.UrlFor(
            "organizations.show",
            lambda o: {"org": o},
            description="The organization page URL",
            readonly=True,
            fallback_endpoint="api.organization",
        ),
        "logo": fields.ImageField(original=True, description="The organization logo URL"),
        "logo_thumbnail": fields.ImageField(
            attribute="logo",
            size=BIGGEST_LOGO_SIZE,
            description="The organization logo thumbnail URL. This is the square "
            "({0}x{0}) and cropped version.".format(BIGGEST_LOGO_SIZE),
        ),
        "members": fields.List(
            fields.Nested(member_fields, description="The organization members")
        ),
        "badges": fields.List(
            fields.Nested(badge_fields), description="The organization badges", readonly=True
        ),
        "extras": fields.Raw(description="Extras attributes as key-value pairs"),
    },
)

org_page_fields = api.model("OrganizationPage", fields.pager(org_fields))


refuse_membership_fields = api.model(
    "RefuseMembership",
    {
        "comment": fields.String(description="The refusal comment."),
    },
)


org_role_fields = api.model(
    "OrganizationRole",
    {
        "id": fields.String(description="The role identifier"),
        "label": fields.String(description="The role label"),
    },
)


org_suggestion_fields = api.model(
    "OrganizationSuggestion",
    {
        "id": fields.String(description="The organization identifier", readonly=True),
        "name": fields.String(description="The organization name", readonly=True),
        "acronym": fields.String(description="The organization acronym", readonly=True),
        "slug": fields.String(description="The organization permalink string", readonly=True),
        "image_url": fields.ImageField(
            size=BIGGEST_LOGO_SIZE, description="The organization logo URL", readonly=True
        ),
        "page": fields.UrlFor(
            "organizations.show_redirect",
            lambda o: {"org": o["slug"]},
            description="The organization web page URL",
            readonly=True,
            fallback_endpoint="api.organization",
        ),
    },
)
