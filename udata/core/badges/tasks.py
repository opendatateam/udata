# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

from udata import mail
from udata.i18n import lazy_gettext as _
from udata.models import Organization
from udata.tasks import task, get_logger

from .signals import on_badge_added

log = get_logger(__name__)


def connect(signal):
    def wrapper(func):
        t = task(func)

        def call_task(badge, **kwargs):
            t.delay(badge, **kwargs)

        signal.connect(call_task, weak=False)
        return t
    return wrapper


def owner_recipients(badge):
    if badge.subject.organization:
        members = badge.subject.organization.members
    else:
        members = badge.subject.members
    return [m.user for m in members]


@connect(on_badge_added)
def notify_badge_added(badge):
    if isinstance(badge.subject, Organization):
        recipients = owner_recipients(badge)
        subject = _('Your %(type)s gain a new badge',
                    type=badge.subject.verbose_name)
        mail.send(subject, recipients, 'badge_added', badge=badge)
    else:
        log.warning('Unrecognized badge subject type %s', type(badge.subject))
