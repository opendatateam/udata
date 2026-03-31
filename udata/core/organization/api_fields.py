from udata.api import api, fields
from udata.core.user.models import User

from .constants import BIGGEST_LOGO_SIZE, DEFAULT_ROLE, MEMBERSHIP_STATUS, ORG_ROLES, REQUEST_TYPES
from .models import Member, Organization

generic_reference_fields = api.model(
    "GenericReference",
    {
        "class": fields.String(attribute=lambda o: o.__class__.__name__),
        "id": fields.String(attribute=lambda o: str(o.id)),
    },
)

request_fields = api.model(
    "MembershipRequest",
    {
        "id": fields.String(readonly=True),
        "user": fields.Nested(User.__ref_fields__, allow_null=True),
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
        "organization": fields.Nested(Organization.__ref_fields__),
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

member_fields = Member.__read_fields__


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
