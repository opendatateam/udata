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
        subject=_("Votre invitation à rejoindre une organisation a été acceptée"),
        paragraphs=[
            ParagraphWithLinks(
                _(
                    "Bonne nouvelle ! Votre demande pour rejoindre l’organisation %(org)s a été approuvée.",
                    org=org,
                )
            ),
            MailCTA(_("Voir l'organisation"), cdata_url(f"/admin/organizations/{org.id}/")),
        ],
    )


def new_member(org: Organization) -> MailMessage:
    return MailMessage(
        subject=_("Vous avez été ajouté comme membre d'une organisation"),
        paragraphs=[
            ParagraphWithLinks(
                _(
                    "Bonne nouvelle ! Vous êtes maintenant membre de %(org)s.",
                    org=org,
                )
            ),
            MailCTA(_("Voir l'organisation"), cdata_url(f"/admin/organizations/{org.id}/")),
        ],
    )


def badge_added_certified(org: Organization) -> MailMessage:
    return MailMessage(
        subject=_("Votre organisation a été certifiée"),
        paragraphs=[
            ParagraphWithLinks(
                _(
                    "Bonne nouvelle ! Votre organisation %(org)s a été certifiée par notre équipe. Un badge est désormais associé à votre organisation.",
                    org=org,
                )
            ),
            MailCTA(_("Voir l'organisation"), cdata_url(f"/admin/organizations/{org.id}/")),
        ],
    )


def badge_added_public_service(org: Organization) -> MailMessage:
    return MailMessage(
        subject=_("Votre organisation a été identifiée comme un service public"),
        paragraphs=[
            ParagraphWithLinks(
                _(
                    "Bonne nouvelle ! Votre organisation %(org)s a été identifiée par notre équipe comme un service public. Un badge est désormais associé à votre organisation.",
                    org=org,
                )
            ),
            MailCTA(_("Voir l'organisation"), cdata_url(f"/admin/organizations/{org.id}/")),
        ],
    )


def badge_added_local_authority(org: Organization) -> MailMessage:
    return MailMessage(
        subject=_("Votre organisation a été identifiée comme une collectivité territoriale"),
        paragraphs=[
            ParagraphWithLinks(
                _(
                    "Bonne nouvelle ! Votre organisation %(org)s a été identifiée par notre équipe comme une collectivité territoriale. Un badge est désormais associé à votre organisation.",
                    org=org,
                )
            ),
            MailCTA(_("Voir l'organisation"), cdata_url(f"/admin/organizations/{org.id}/")),
        ],
    )


def badge_added_company(org: Organization) -> MailMessage:
    return MailMessage(
        subject=_("Votre organisation a été identifiée comme une entreprise"),
        paragraphs=[
            ParagraphWithLinks(
                _(
                    "Votre organisation %(org)s a été identifiée par notre équipe comme une entreprise. Un badge est désormais associé à votre organisation.",
                    org=org,
                )
            ),
            MailCTA(_("Voir l'organisation"), cdata_url(f"/admin/organizations/{org.id}/")),
        ],
    )


def badge_added_association(org: Organization) -> MailMessage:
    return MailMessage(
        subject=_("Votre organisation a été identifiée comme une association"),
        paragraphs=[
            ParagraphWithLinks(
                _(
                    "Votre organisation %(org)s a été identifiée par notre équipe comme une association. Un badge est désormais associé à votre organisation.",
                    org=org,
                )
            ),
            MailCTA(_("Voir l'organisation"), cdata_url(f"/admin/organizations/{org.id}/")),
        ],
    )
