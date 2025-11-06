from udata.core.organization.models import MembershipRequest, Organization
from udata.i18n import lazy_gettext as _
from udata.mail import LabelledContent, MailCTA, MailMessage, ParagraphWithLinks
from udata.uris import cdata_url


def new_membership_request(org: Organization, request: MembershipRequest) -> MailMessage:
    return MailMessage(
        subject=_("New membership request"),
        paragraphs=[
            ParagraphWithLinks(
                _(
                    "You received a membership request from %(user)s for your organization %(org)s",
                    user=request.user,
                    org=org,
                )
            ),
            LabelledContent(_("Reason for the request:"), request.comment),
            MailCTA(_("See the request"), cdata_url(f"/admin/organizations/{org.id}/members/")),
        ],
    )


def membership_refused(org: Organization) -> MailMessage:
    return MailMessage(
        subject=_("Membership refused"),
        paragraphs=[
            ParagraphWithLinks(
                _(
                    "Your membership for the organization %(org)s has been refused",
                    org=org,
                )
            ),
        ],
    )


def membership_accepted(org: Organization) -> MailMessage:
    return MailMessage(
        subject=_("Your invitation to join an organization has been accepted"),
        paragraphs=[
            ParagraphWithLinks(
                _(
                    "Good news! Your request to join the organization %(org)s has been approved.",
                    org=org,
                )
            ),
            MailCTA(
                _("View the organization"), cdata_url(f"/admin/organizations/{org.id}/datasets")
            ),
        ],
    )


def new_member(org: Organization) -> MailMessage:
    return MailMessage(
        subject=_("You have been added as a member of an organization"),
        paragraphs=[
            ParagraphWithLinks(
                _(
                    "Good news! You are now a member of %(org)s.",
                    org=org,
                )
            ),
            MailCTA(
                _("View the organization"), cdata_url(f"/admin/organizations/{org.id}/datasets")
            ),
        ],
    )


def badge_added_certified(org: Organization) -> MailMessage:
    return MailMessage(
        subject=_("Your organization has been certified"),
        paragraphs=[
            ParagraphWithLinks(
                _(
                    "Good news! Your organization %(org)s has been certified by our team. A badge is now associated with your organization.",
                    org=org,
                )
            ),
            MailCTA(_("View the organization"), org.self_web_url()),
        ],
    )


def badge_added_public_service(org: Organization) -> MailMessage:
    return MailMessage(
        subject=_("Your organization has been identified as a public service"),
        paragraphs=[
            ParagraphWithLinks(
                _(
                    "Good news! Your organization %(org)s has been identified by our team as a public service. A badge is now associated with your organization.",
                    org=org,
                )
            ),
            MailCTA(_("View the organization"), org.self_web_url()),
        ],
    )


def badge_added_local_authority(org: Organization) -> MailMessage:
    return MailMessage(
        subject=_("Your organization has been identified as a local authority"),
        paragraphs=[
            ParagraphWithLinks(
                _(
                    "Good news! Your organization %(org)s has been identified by our team as a local authority. A badge is now associated with your organization.",
                    org=org,
                )
            ),
            MailCTA(_("View the organization"), org.self_web_url()),
        ],
    )


def badge_added_company(org: Organization) -> MailMessage:
    return MailMessage(
        subject=_("Your organization has been identified as a company"),
        paragraphs=[
            ParagraphWithLinks(
                _(
                    "Your organization %(org)s has been identified by our team as a company. A badge is now associated with your organization.",
                    org=org,
                )
            ),
            MailCTA(_("View the organization"), org.self_web_url()),
        ],
    )


def badge_added_association(org: Organization) -> MailMessage:
    return MailMessage(
        subject=_("Your organization has been identified as an association"),
        paragraphs=[
            ParagraphWithLinks(
                _(
                    "Your organization %(org)s has been identified by our team as an association. A badge is now associated with your organization.",
                    org=org,
                )
            ),
            MailCTA(_("View the organization"), org.self_web_url()),
        ],
    )
