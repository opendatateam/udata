from udata.core.discussions.models import Discussion, Message
from udata.i18n import lazy_gettext as _
from udata.mail import LabelledContent, MailCTA, MailMessage, ParagraphWithLinks


def new_discussion(discussion: Discussion, url: str) -> MailMessage:
    subject_type = discussion.notification_subject_type
    return MailMessage(
        subject=_(
            "A new discussion has been opened on your %(type)s",
            type=subject_type,
        ),
        paragraphs=[
            ParagraphWithLinks(
                _(
                    "You have a new discussion from %(user_or_org)s on your %(type)s %(object)s",
                    user_or_org=discussion.organization or discussion.user,
                    type=subject_type,
                    object=discussion.subject,
                )
            ),
            LabelledContent(_("Discussion title:"), discussion.title, inline=True),
            LabelledContent(_("Comment:"), discussion.discussion[0].content),
            MailCTA(_("Reply"), url),
        ],
    )


def new_discussion_comment(discussion: Discussion, comment: Message, url: str) -> MailMessage:
    return MailMessage(
        subject=_("A new comment has been added to a discussion"),
        paragraphs=[
            ParagraphWithLinks(
                _(
                    "You have a new comment from %(user_or_org)s on your %(type)s %(object)s",
                    user_or_org=comment.posted_by_org_or_user,
                    type=discussion.notification_subject_type,
                    object=discussion.subject,
                )
            ),
            LabelledContent(_("Discussion title:"), discussion.title, inline=True),
            LabelledContent(_("Comment:"), comment.content),
            MailCTA(_("Reply"), url),
        ],
    )


def discussion_closed(discussion: Discussion, comment: Message | None, url: str) -> MailMessage:
    return MailMessage(
        subject=_("A discussion has been closed"),
        paragraphs=[
            ParagraphWithLinks(
                _(
                    "The discussion you participated in on the %(type)s %(object)s has been closed by %(user_or_org)s.",
                    user_or_org=discussion.closed_by_org_or_user,
                    type=discussion.notification_subject_type,
                    object=discussion.subject,
                )
            ),
            LabelledContent(_("Discussion title:"), discussion.title, inline=True),
            LabelledContent(_("Comment:"), comment.content) if comment else None,
            MailCTA(_("View the discussion"), url),
        ],
    )
