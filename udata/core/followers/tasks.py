# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

from udata import mail
from udata.i18n import lazy_gettext as _
from udata.models import Dataset, Reuse, Organization, User
from udata.tasks import task, get_logger

from .signals import on_follow

log = get_logger(__name__)


@on_follow.connect
def notify_on_follow(follow):
    notify_new_follower.delay(follow)


@task
def notify_new_follower(follow):
    if isinstance(follow.following, User):
        subject = _('%(user)s followed you', user=follow.follower)
        mail.send(subject, follow.following, 'new_follower', follow=follow)
    elif isinstance(follow.following, Organization):
        subject = _('%(user)s followed your organization',
                    user=follow.follower)
        recipients = [m.user for m in follow.following.members]
        mail.send(subject, recipients, 'new_follower_org', follow=follow)
    elif isinstance(follow.following, Dataset):
        pass
    elif isinstance(follow.following, Reuse):
        pass
