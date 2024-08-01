from udata import mail
from udata.core.dataset.models import Dataset
from udata.core.post.models import Post
from udata.core.reuse.models import Reuse
from udata.i18n import lazy_gettext as _
from udata.tasks import connect, get_logger

from .models import Discussion
from .signals import on_discussion_closed, on_new_discussion, on_new_discussion_comment

log = get_logger(__name__)


def owner_recipients(discussion):
    if getattr(discussion.subject, "organization", None):
        return [m.user for m in discussion.subject.organization.members]
    elif getattr(discussion.subject, "owner", None):
        return [discussion.subject.owner]
    else:
        return []


@connect(on_new_discussion, by_id=True)
def notify_new_discussion(discussion_id):
    discussion = Discussion.objects.get(pk=discussion_id)
    if isinstance(discussion.subject, (Dataset, Reuse, Post)):
        recipients = owner_recipients(discussion)
        subject = _("Your %(type)s have a new discussion", type=discussion.subject.verbose_name)
        mail.send(
            subject,
            recipients,
            "new_discussion",
            discussion=discussion,
            message=discussion.discussion[0],
        )
    else:
        log.warning("Unrecognized discussion subject type %s", type(discussion.subject))


@connect(on_new_discussion_comment, by_id=True)
def notify_new_discussion_comment(discussion_id, message=None):
    discussion = Discussion.objects.get(pk=discussion_id)
    message = discussion.discussion[message]
    if isinstance(discussion.subject, (Dataset, Reuse, Post)):
        recipients = owner_recipients(discussion) + [m.posted_by for m in discussion.discussion]
        recipients = list({u.id: u for u in recipients if u != message.posted_by}.values())
        subject = _("%(user)s commented your discussion", user=message.posted_by.fullname)

        mail.send(
            subject, recipients, "new_discussion_comment", discussion=discussion, message=message
        )
    else:
        log.warning("Unrecognized discussion subject type %s", type(discussion.subject))


@connect(on_discussion_closed, by_id=True)
def notify_discussion_closed(discussion_id, message=None):
    discussion = Discussion.objects.get(pk=discussion_id)
    message = discussion.discussion[message]
    if isinstance(discussion.subject, (Dataset, Reuse, Post)):
        recipients = owner_recipients(discussion) + [m.posted_by for m in discussion.discussion]
        recipients = list({u.id: u for u in recipients if u != message.posted_by}.values())
        subject = _("A discussion has been closed")
        mail.send(subject, recipients, "discussion_closed", discussion=discussion, message=message)
    else:
        log.warning("Unrecognized discussion subject type %s", type(discussion.subject))
