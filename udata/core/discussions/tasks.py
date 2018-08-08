# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

from udata import mail
from udata.i18n import lazy_gettext as _
from udata.core.dataset.models import Dataset
from udata.core.reuse.models import Reuse
from udata.core.post.models import Post
from udata.tasks import task, get_logger

from .signals import (
    on_new_discussion, on_new_discussion_comment, on_discussion_closed
)

log = get_logger(__name__)


def connect(signal):
    def wrapper(func):
        t = task(func)

        def call_task(discussion, **kwargs):
            t.delay(discussion, **kwargs)

        signal.connect(call_task, weak=False)
        return t
    return wrapper


def owner_recipients(discussion):
    if getattr(discussion.subject, 'organization', None):
        return [m.user for m in discussion.subject.organization.members]
    else:
        return [discussion.subject.owner]


@connect(on_new_discussion)
def notify_new_discussion(discussion):
    if isinstance(discussion.subject, (Dataset, Reuse, Post)):
        recipients = owner_recipients(discussion)
        subject = _('Your %(type)s have a new discussion',
                    type=discussion.subject.verbose_name)
        mail.send(subject, recipients, 'new_discussion',
                  discussion=discussion, message=discussion.discussion[0])
    else:
        log.warning('Unrecognized discussion subject type %s',
                    type(discussion.subject))


@connect(on_new_discussion_comment)
def notify_new_discussion_comment(discussion, **kwargs):
    if isinstance(discussion.subject, (Dataset, Reuse, Post)):
        message = kwargs['message']
        recipients = owner_recipients(discussion) + [
            m.posted_by for m in discussion.discussion]
        recipients = [u for u in set(recipients) if u != message.posted_by]
        subject = _('%(user)s commented your discussion',
                    user=message.posted_by.fullname)
        mail.send(subject, recipients, 'new_discussion_comment',
                  discussion=discussion, message=message)
    else:
        log.warning('Unrecognized discussion subject type %s',
                    type(discussion.subject))


@connect(on_discussion_closed)
def notify_discussion_closed(discussion, **kwargs):
    if isinstance(discussion.subject, (Dataset, Reuse, Post)):
        message = kwargs['message']
        recipients = owner_recipients(discussion) + [
            m.posted_by for m in discussion.discussion]
        recipients = [u for u in set(recipients) if u != message.posted_by]
        subject = _('A discussion has been closed')
        mail.send(subject, recipients, 'discussion_closed',
                  discussion=discussion, message=message)
    else:
        log.warning('Unrecognized discussion subject type %s',
                    type(discussion.subject))
