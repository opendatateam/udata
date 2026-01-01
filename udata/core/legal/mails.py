from flask import current_app
from flask_login import current_user
from flask_restx.inputs import boolean

from udata.core.dataservices.models import Dataservice
from udata.core.dataset.models import Dataset
from udata.core.discussions.models import Discussion, Message
from udata.core.organization.models import Organization
from udata.core.reuse.models import Reuse
from udata.core.user.models import User
from udata.i18n import lazy_gettext as _
from udata.mail import Link, MailMessage, ParagraphWithLinks

DeletableObject = Dataset | Reuse | Dataservice | Organization | User | Discussion | Message


def add_send_legal_notice_argument(parser):
    """Add the send_legal_notice argument to a parser.

    When send_legal_notice=true is passed by an admin, a formal legal notice email
    is sent to the content owner. This email includes terms of use references and
    information about how to contest the deletion (administrative appeal).
    """
    parser.add_argument(
        "send_legal_notice",
        type=boolean,
        default=False,
        location="args",
        help="Send formal legal notice with appeal information to owner (admin only)",
    )
    return parser


def _get_recipients_for_organization(org: Organization) -> list[User]:
    return [m.user for m in org.by_role("admin")]


def _get_recipients_for_owned_object(obj: Dataset | Reuse | Dataservice) -> list[User]:
    if obj.owner:
        return [obj.owner]
    elif obj.organization:
        return _get_recipients_for_organization(obj.organization)
    return []


def send_legal_notice_on_deletion(obj: DeletableObject, args: dict):
    """Send a formal legal notice email when content is deleted by an admin.

    The email is only sent if:
    - send_legal_notice=true was passed in args
    - The current user is a sysadmin
    """
    if not args.get("send_legal_notice") or not current_user.sysadmin:
        return

    if isinstance(obj, Organization):
        recipients = _get_recipients_for_organization(obj)
    elif isinstance(obj, User):
        recipients = [obj]
    elif isinstance(obj, Discussion):
        recipients = [obj.user] if obj.user else []
    elif isinstance(obj, Message):
        recipients = [obj.posted_by] if obj.posted_by else []
    else:
        recipients = _get_recipients_for_owned_object(obj)

    if recipients:
        _content_deleted(obj.verbose_name).send(recipients)


def _content_deleted(content_type_label) -> MailMessage:
    admin = current_user._get_current_object()
    admin_name = f"{admin.first_name} {admin.last_name}"

    terms_of_use_url = current_app.config.get("TERMS_OF_USE_URL")
    terms_of_use_deletion_article = current_app.config.get("TERMS_OF_USE_DELETION_ARTICLE")
    telerecours_url = current_app.config.get("TELERECOURS_URL")

    if terms_of_use_url and terms_of_use_deletion_article:
        terms_paragraph = ParagraphWithLinks(
            _(
                'Our %(terms_link)s specify in point %(article)s that the platform is not "intended '
                "to disseminate advertising content, promotions of private interests, content contrary "
                "to public order, illegal content, spam and any contribution violating the applicable "
                "legal framework. The Editor reserves the right, without prior notice, to remove or "
                "make inaccessible content published on the Platform that has no connection with its "
                'Purpose. The Editor does not carry out "a priori" control over publications. As soon '
                "as the Editor becomes aware of content contrary to these terms of use, it acts quickly "
                'to remove or make it inaccessible".',
                terms_link=Link(_("terms of use"), terms_of_use_url),
                article=terms_of_use_deletion_article,
            )
        )
    else:
        terms_paragraph = _(
            'The platform is not "intended to disseminate advertising content, promotions of '
            "private interests, content contrary to public order, illegal content, spam and any "
            "contribution violating the applicable legal framework. The Editor reserves the right, "
            "without prior notice, to remove or make inaccessible content published on the Platform "
            'that has no connection with its Purpose. The Editor does not carry out "a priori" '
            "control over publications. As soon as the Editor becomes aware of content contrary to "
            'these terms of use, it acts quickly to remove or make it inaccessible".'
        )

    if telerecours_url:
        appeal_paragraph = ParagraphWithLinks(
            _(
                "You may contest this decision within two months of its notification by filing "
                "an administrative appeal (recours gracieux ou hiérarchique). You may also bring "
                'the matter before the administrative court via the "%(telerecours_link)s" application.',
                telerecours_link=Link(_("Télérecours citoyens"), telerecours_url),
            )
        )
    else:
        appeal_paragraph = _("You may contest this decision by contacting us.")

    paragraphs = [
        _("Your %(content_type)s has been deleted.", content_type=content_type_label),
        terms_paragraph,
        appeal_paragraph,
        _("Best regards,"),
        admin_name,
        _("%(site)s team member", site=current_app.config.get("SITE_TITLE", "data.gouv.fr")),
    ]

    return MailMessage(
        subject=_("Deletion of your %(content_type)s", content_type=content_type_label),
        paragraphs=paragraphs,
    )
