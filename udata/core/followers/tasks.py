# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import warnings

from udata import mail
from udata.i18n import lazy_gettext as _
from udata.models import Dataset, Reuse, Organization, User
from udata.tasks import connect, get_logger

from .models import Follow
from .signals import on_follow

log = get_logger(__name__)


@connect(on_follow, by_id=True)
def notify_new_follower(follow_id):
    if isinstance(follow_id, Follow):  # TODO: Remove this branch in udata 2.0
        warnings.warn(
            'Using documents as task parameter is deprecated and '
            'will be removed in udata 2.0',
            DeprecationWarning
        )
        follow = follow_id
    else:
        follow = Follow.objects.get(pk=follow_id)

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
