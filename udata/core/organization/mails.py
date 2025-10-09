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
                    "Vous avez reçu une demande d'adhésion de %(user)s sur votre organisation %(org)s",
                    user=request.user,
                    org=org,
                )
            ),
            LabelledContent(_("Motif de la demande:"), request.comment),
            MailCTA(_("See the request"), cdata_url(f"/admin/organizations/{org.id}/members/")),
        ],
    )
