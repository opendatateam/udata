from udata.core.discussions.models import Discussion, Message
from udata.i18n import lazy_gettext as _
from udata.mail import LabelledContent, MailCTA, MailMessage, ParagraphWithLinks


def new_discussion(discussion: Discussion) -> MailMessage:
    return MailMessage(
        subject=_(
            "A new discussion has been opened on your %(type)s",
            type=discussion.subject.verbose_name,
        ),
        paragraphs=[
            ParagraphWithLinks(
                _(
                    "You have a new discussion from %(user_or_org)s on your %(type)s %(object)s",
                    user_or_org=discussion.organization or discussion.user,
                    type=discussion.subject.verbose_name,
                    object=discussion.subject,
                )
            ),
            LabelledContent(_("Discussion title:"), discussion.title, inline=True),
            LabelledContent(_("Comment:"), discussion.discussion[0].content),
            MailCTA(_("Reply"), discussion.url_for()),
        ],
    )


def new_discussion_comment(discussion: Discussion, comment: Message) -> MailMessage:
    return MailMessage(
        subject=_("A new comment has been added to a discussion"),
        paragraphs=[
            ParagraphWithLinks(
                _(
                    "You have a new comment from %(user_or_org)s on your %(type)s %(object)s",
                    user_or_org=comment.posted_by_org_or_user,
                    type=discussion.subject.verbose_name,
                    object=discussion.subject,
                )
            ),
            LabelledContent(_("Discussion title:"), discussion.title, inline=True),
            LabelledContent(_("Comment:"), comment.content),
            MailCTA(_("Reply"), discussion.url_for()),
        ],
    )


def discussion_closed(discussion: Discussion, comment: Message | None) -> MailMessage:
    return MailMessage(
        subject=_("A discussion has been closed"),
        paragraphs=[
            ParagraphWithLinks(
                _(
                    "The discussion you participated in on the %(type)s %(object)s has been closed by %(user_or_org)s.",
                    user_or_org=discussion.closed_by_org_or_user,
                    type=discussion.subject.verbose_name,
                    object=discussion.subject,
                )
            ),
            LabelledContent(_("Discussion title:"), discussion.title, inline=True),
            LabelledContent(_("Comment:"), comment.content) if comment else None,
            MailCTA(_("View the discussion"), discussion.url_for()),
        ],
    )
