from udata.tasks import connect, get_logger

from . import mails
from .constants import NOTIFY_DISCUSSION_SUBJECTS
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
    if isinstance(discussion.subject, NOTIFY_DISCUSSION_SUBJECTS):
        mails.new_discussion(discussion).send(owner_recipients(discussion))
    else:
        log.warning("Unrecognized discussion subject type %s", type(discussion.subject))


@connect(on_new_discussion_comment, by_id=True)
def notify_new_discussion_comment(discussion_id, message=None):
    discussion = Discussion.objects.get(pk=discussion_id)
    message = discussion.discussion[message]
    if isinstance(discussion.subject, NOTIFY_DISCUSSION_SUBJECTS):
        recipients = owner_recipients(discussion) + [m.posted_by for m in discussion.discussion]
        recipients = list({u.id: u for u in recipients if u != message.posted_by}.values())
        mails.new_discussion_comment(discussion, message).send(recipients)
    else:
        log.warning("Unrecognized discussion subject type %s", type(discussion.subject))


@connect(on_discussion_closed, by_id=True)
def notify_discussion_closed(discussion_id, message=None):
    discussion = Discussion.objects.get(pk=discussion_id)
    message = discussion.discussion[message] if message else None
    if isinstance(discussion.subject, NOTIFY_DISCUSSION_SUBJECTS):
        recipients = owner_recipients(discussion) + [m.posted_by for m in discussion.discussion]
        recipients = list({u.id: u for u in recipients if u != discussion.closed_by}.values())
        mails.discussion_closed(discussion, message).send(recipients)
    else:
        log.warning("Unrecognized discussion subject type %s", type(discussion.subject))
