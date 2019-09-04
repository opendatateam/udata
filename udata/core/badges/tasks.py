# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import warnings

from udata import mail
from udata.i18n import lazy_gettext as _
from udata.models import Organization, CERTIFIED, PUBLIC_SERVICE
from udata.tasks import task, get_logger

from .signals import on_badge_added

log = get_logger(__name__)


def notify_new_badge(cls, kind):
    def wrapper(func):
        t = task(func)

        def call_task(sender, **kwargs):
            if isinstance(sender, cls) and kwargs.get('kind') == kind:
                t.delay(str(sender.pk))

        on_badge_added.connect(call_task, weak=False)
        return t
    return wrapper


@task
def notify_badge_added_certified(sender, kind=''):
    '''
    Send an email when a `CERTIFIED` badge is added to an `Organization`

    Parameters
    ----------
    sender
        The object that emitted the event.
    kind: str
        The kind of `Badge` object awarded.
    '''
    warnings.warn(
        'Using documents as task parameter is deprecated and '
        'will be removed in udata 2.0',
        DeprecationWarning
    )
    if kind == CERTIFIED and isinstance(sender, Organization):
        recipients = [member.user for member in sender.members]
        subject = _(
            'Your organization "%(name)s" has been certified',
            name=sender.name
        )
        mail.send(
            subject,
            recipients,
            'badge_added_certified',
            organization=sender,
            badge=sender.get_badge(kind)
        )


@task
def notify_badge_added_public_service(sender, kind=''):
    '''
    Send an email when a `PUBLIC_SERVICE` badge is added to an `Organization`

    Parameters
    ----------
    sender
        The object that emitted the event.
    kind: str
        The kind of `Badge` object awarded.
    '''
    warnings.warn(
        'Using documents as task parameter is deprecated and '
        'will be removed in udata 2.0',
        DeprecationWarning
    )
    if kind == PUBLIC_SERVICE and isinstance(sender, Organization):
        recipients = [member.user for member in sender.members]
        subject = _(
            'Your organization "%(name)s" has been identified as public service',
            name=sender.name
        )
        mail.send(
            subject,
            recipients,
            'badge_added_public_service',
            organization=sender,
            badge=sender.get_badge(kind)
        )
