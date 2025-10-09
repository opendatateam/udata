from udata.core.discussions.models import Discussion, Message
from udata.i18n import lazy_gettext as _
from udata.mail import LabelledContent, MailCTA, MailMessage, ParagraphWithLinks


def new_discussion(discussion: Discussion) -> MailMessage:
    return MailMessage(
        subject=_(
            "Une nouvelle discussion a été ouverte sur votre %(type)s",
            type=discussion.subject.verbose_name,
        ),
        paragraphs=[
            ParagraphWithLinks(
                _(
                    "Vous avez un nouvelle discussion de %(user_or_org)s sur votre %(type)s %(object)s",
                    user_or_org=discussion.organization or discussion.user,
                    type=discussion.subject.verbose_name,
                    object=discussion.subject,
                )
            ),
            LabelledContent(_("Titre de la discussion :"), discussion.title, inline=True),
            LabelledContent(_("Commentaire :"), discussion.discussion[0].content),
            MailCTA(_("Répondre"), discussion.url_for()),
        ],
    )


def new_discussion_comment(discussion: Discussion, comment: Message) -> MailMessage:
    return MailMessage(
        subject=_("Un nouveau commentaire a été ajouté dans une discussion"),
        paragraphs=[
            ParagraphWithLinks(
                _(
                    "Vous avez un nouveau commentaire de %(user_or_org)s sur votre %(type)s %(object)s",
                    user_or_org=comment.posted_by_org_or_user,
                    type=discussion.subject.verbose_name,
                    object=discussion.subject,
                )
            ),
            LabelledContent(_("Titre de la discussion :"), discussion.title, inline=True),
            LabelledContent(_("Commentaire :"), comment.content),
            MailCTA(_("Répondre"), discussion.url_for()),
        ],
    )


def discussion_closed(discussion: Discussion, comment: Message | None) -> MailMessage:
    return MailMessage(
        subject=_("Une discussion a été clôturée"),
        paragraphs=[
            ParagraphWithLinks(
                _(
                    "La discussion à laquelle vous avez participé sur le %(type)s %(object)s a été clôturée par %(user_or_org)s.",
                    user_or_org=discussion.closed_by_org_or_user,
                    type=discussion.subject.verbose_name,
                    object=discussion.subject,
                )
            ),
            LabelledContent(_("Titre de la discussion :"), discussion.title, inline=True),
            LabelledContent(_("Commentaire :"), comment.content) if comment else None,
            MailCTA(_("Voir la discussion"), discussion.url_for()),
        ],
    )
