# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import logging

from udata import mail
from udata.i18n import lazy_gettext as _
from udata.tasks import task

log = logging.getLogger(__name__)


@task(route='high.mail')
def send_test_mail(user):
    mail.send(_('Test mail'), user, 'test')
