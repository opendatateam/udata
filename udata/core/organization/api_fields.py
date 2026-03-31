from flask import request

from udata.api import api, fields
from udata.auth.helpers import current_user_is_admin_or_self

from .constants import BIGGEST_LOGO_SIZE, DEFAULT_ROLE, MEMBERSHIP_STATUS, ORG_ROLES, REQUEST_TYPES
from .models import Organization

generic_reference_fields = api.model(
    "GenericReference",
    {
        "class": fields.String(attribute=lambda o: o.__class__.__name__),
        "id": fields.String(attribute=lambda o: str(o.id)),
    },
)

org_ref_fields = Organization.__ref_fields__


def check_can_access_user_private_info():
    # This endpoint is secure, only organization member has access.
    if request.endpoint == "api.request_membership":
        return True

    if request.endpoint != "api.organization":
        return False

    org = request.view_args.get("org")
    if org is None:
        return False

    return org.permissions["private"].can()


def member_email_with_visibility_check(email):
    if current_user_is_admin_or_self():
        return email
    name, domain = email.split("@")
    if check_can_access_user_private_info():
        # Obfuscate email partially for other members
        name = name[:2] + "*" * (len(name) - 2)
        return f"{name}@{domain}"
    # Return only domain for other users
    return f"***@{domain}"


# This import is not at the top of the file to avoid circular imports
from udata.core.user.api_fields import user_ref_fields  # noqa

member_user_with_email_fields = api.inherit(
    "MemberUserWithEmail",
    user_ref_fields,
    {
        "email": fields.Raw(
            attribute=lambda o: member_email_with_visibility_check(o.email),
            description="The user email (only present on show organization endpoint if the current user is member of the organization: admin or editor)",
            readonly=True,
        ),
        "last_login_at": fields.Raw(
            attribute=lambda o: (
                o.current_login_at if check_can_access_user_private_info() else None
            ),
            description="The user last connection date (only present on show organization endpoint if the current user is member of the organization: admin or editor)",
            readonly=True,
        ),
    },
)

request_fields = api.model(
    "MembershipRequest",
    {
        "id": fields.String(readonly=True),
        "user": fields.Nested(member_user_with_email_fields, allow_null=True),
        "email": fields.String(description="Email for non-registered user invitations"),
        "kind": fields.String(
            description="The request kind (request or invitation)",
            enum=list(REQUEST_TYPES),
            default="request",
        ),
        "created": fields.ISODateTime(description="The request creation date", readonly=True),
        "status": fields.String(
            description="The current request status", required=True, enum=list(MEMBERSHIP_STATUS)
        ),
        "role": fields.String(
            description="The role to assign", enum=list(ORG_ROLES), default=DEFAULT_ROLE
        ),
        "comment": fields.String(description="A request comment from the user"),
        "assignments": fields.List(
            fields.Nested(generic_reference_fields),
            description="Objects to assign on acceptance (for partial_editor invitations)",
        ),
    },
)

invite_fields = api.model(
    "MembershipInvite",
    {
        "user": fields.String(description="User ID to invite"),
        "email": fields.String(description="Email to invite (if user not registered)"),
        "role": fields.String(
            description="The role to assign", enum=list(ORG_ROLES), default=DEFAULT_ROLE
        ),
        "comment": fields.String(description="Invitation message"),
        "assignments": fields.List(
            fields.Nested(generic_reference_fields),
            description="Objects to assign on acceptance (for partial_editor invitations)",
        ),
    },
)

pending_invitation_fields = api.model(
    "PendingInvitation",
    {
        "id": fields.String(readonly=True),
        "organization": fields.Nested(org_ref_fields),
        "role": fields.String(
            description="The role to assign", enum=list(ORG_ROLES), default=DEFAULT_ROLE
        ),
        "comment": fields.String(description="Invitation message"),
        "created": fields.ISODateTime(description="The invitation creation date", readonly=True),
        "assignments": fields.List(
            fields.Nested(generic_reference_fields),
            description="Objects to assign on acceptance (for partial_editor invitations)",
        ),
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
        "label": fields.String(readonly=True),
        "since": fields.ISODateTime(
            description="The date the user joined the organization", readonly=True
        ),
    },
)

# Patch auto-generated read_fields to use email-enriched member serialization.
# Cannot be set at model definition time due to circular imports
# (models.py → user/api_fields.py → organization/api_fields.py → models.py).
Organization.__read_fields__["members"] = fields.List(
    fields.Nested(member_fields, description="The organization members")
)

org_fields = Organization.__read_fields__
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
        "page": fields.String(description="The organization web page URL", readonly=True),
    },
)
