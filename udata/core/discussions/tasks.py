from udata.core.discussions.notifications import (
    DiscussionClosed,
    NewDiscussion,
    NewDiscussionComment,
)
from udata.features.notifications.models import Notification
from udata.tasks import connect

from .models import Discussion
from .signals import on_discussion_closed, on_new_discussion, on_new_discussion_comment


def _mark_handled(user, discussion):
    """Answering or closing a discussion resolves whatever the author still had
    pending on it."""
    Notification.objects.filter(user=user, details__discussion=discussion).mark_handled()


@connect(on_new_discussion, by_id=True)
def notify_new_discussion(discussion_id):
    discussion = Discussion.objects.get(pk=discussion_id)

    NewDiscussion(discussion).dispatch()


@connect(on_new_discussion_comment, by_id=True)
def notify_new_discussion_comment(discussion_id, message=None):
    discussion = Discussion.objects.get(pk=discussion_id)
    message = discussion.discussion[message]

    _mark_handled(message.posted_by, discussion)
    NewDiscussionComment(discussion, message).dispatch()


@connect(on_discussion_closed, by_id=True)
def notify_discussion_closed(discussion_id, message=None):
    discussion = Discussion.objects.get(pk=discussion_id)
    message = discussion.discussion[message] if message else None

    _mark_handled(discussion.closed_by, discussion)
    DiscussionClosed(discussion, message).dispatch()
