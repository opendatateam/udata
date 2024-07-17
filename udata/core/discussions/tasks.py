import fnmatch

from urllib.parse import urlparse

from flask import current_app

from udata import mail
from udata.i18n import lazy_gettext as _
from udata.core.dataset.models import Dataset
from udata.core.post.models import Post
from udata.core.reuse.models import Reuse
from udata.core.topic.models import Topic
from udata.tasks import connect, get_logger

from .models import Discussion
from .signals import (
    on_new_discussion, on_new_discussion_comment, on_discussion_closed
)

log = get_logger(__name__)


def owner_recipients(discussion):
    if getattr(discussion.subject, 'organization', None):
        return [m.user for m in discussion.subject.organization.members]
    elif getattr(discussion.subject, 'owner', None):
        return [discussion.subject.owner]
    else:
        return []


def get_external_url(discussion):
    url = None
    if (meta_url := discussion.extras.get('notification', {}).get('external_url')):
        meta_url_parsed = urlparse(meta_url)
        if any(
            fnmatch.fnmatch(meta_url_parsed.netloc, pattern)
            for pattern in current_app.config['DISCUSSION_ALLOWED_EXTERNAL_DOMAINS']
        ):
            url = f'{meta_url}#discussion-{discussion.id}'
    if not url:
        url = getattr(discussion, 'external_url', None)
    return url


def get_subject_type(discussion):
    if (meta_name := discussion.extras.get('notification', {}).get('model_name')):
        if meta_name in current_app.config['DISCUSSION_ALTERNATE_MODEL_NAMES']:
            return meta_name
    return discussion.subject.verbose_name


@connect(on_new_discussion, by_id=True)
def notify_new_discussion(discussion_id):
    discussion = Discussion.objects.get(pk=discussion_id)
    if isinstance(discussion.subject, (Dataset, Reuse, Post, Topic)):
        recipients = owner_recipients(discussion)
        subject_type = get_subject_type(discussion)
        subject = _('Your %(type)s have a new discussion',
                    type=subject_type)
        external_url = get_external_url(discussion)
        if external_url:
            mail.send(
                subject,
                recipients,
                'new_discussion',
                discussion=discussion,
                message=discussion.discussion[0],
                external_url=external_url,
                subject_type=subject_type
            )
        else:
            log.warning(f'No external url could be computed for discussion {discussion.id}')
    else:
        log.warning('Unrecognized discussion subject type %s',
                    type(discussion.subject))


@connect(on_new_discussion_comment, by_id=True)
def notify_new_discussion_comment(discussion_id, message=None):
    discussion = Discussion.objects.get(pk=discussion_id)
    message = discussion.discussion[message]
    if isinstance(discussion.subject, (Dataset, Reuse, Post, Topic)):
        recipients = owner_recipients(discussion) + [
            m.posted_by for m in discussion.discussion]
        recipients = list({u.id: u for u in recipients if u != message.posted_by}.values())
        subject = _('%(user)s commented your discussion',
                    user=message.posted_by.fullname)
        external_url = get_external_url(discussion)
        if external_url:
            mail.send(
                subject,
                recipients,
                'new_discussion_comment',
                discussion=discussion,
                message=message,
                external_url=external_url,
                subject_type=get_subject_type(discussion)
            )
        else:
            log.warning(f'No external url could be computed for discussion {discussion.id}')
    else:
        log.warning('Unrecognized discussion subject type %s',
                    type(discussion.subject))


@connect(on_discussion_closed, by_id=True)
def notify_discussion_closed(discussion_id, message=None):
    discussion = Discussion.objects.get(pk=discussion_id)
    message = discussion.discussion[message]
    if isinstance(discussion.subject, (Dataset, Reuse, Post, Topic)):
        recipients = owner_recipients(discussion) + [
            m.posted_by for m in discussion.discussion]
        recipients = list({u.id: u for u in recipients if u != message.posted_by}.values())
        subject = _('A discussion has been closed')
        external_url = get_external_url(discussion)
        if external_url:
            mail.send(
                subject,
                recipients,
                'discussion_closed',
                discussion=discussion,
                message=message,
                external_url=external_url,
                subject_type=get_subject_type(discussion),
            )
        else:
            log.warning(f'No external url could be computed for discussion {discussion.id}')
    else:
        log.warning('Unrecognized discussion subject type %s',
                    type(discussion.subject))
