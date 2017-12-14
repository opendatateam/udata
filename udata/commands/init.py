# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from flask_script import prompt_bool

from udata.commands import manager, IS_INTERACTIVE, green
from udata.core.dataset.commands import licenses
from udata.core.user import commands as user_commands
from udata.i18n import lazy_gettext as _
from udata.search.commands import index

from .db import migrate
from .fixtures import generate_fixtures

log = logging.getLogger(__name__)


@manager.command
def init():
    '''Initialize your udata instance (search index, user, sample data...)'''

    log.info('Apply DB migrations if needed')
    migrate(record=True)

    index()

    if IS_INTERACTIVE:
        text = _('Do you want to create a superadmin user?')
        if prompt_bool(text, default=True):
            user = user_commands.create()
            user_commands.set_admin(user.email)

        text = _('Do you want to import some data-related license?')
        if prompt_bool(text, default=True):
            licenses()

        text = _('Do you want to create some sample data?')
        if prompt_bool(text, default=True):
            generate_fixtures()

    log.info(green(_('Your udata instance is ready!')))
