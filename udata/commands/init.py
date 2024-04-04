import logging

import click
from flask import current_app

from udata.commands import cli, success, IS_TTY
from udata.core.dataset.commands import licenses
from udata.core.spatial.commands import load as spatial_load
from udata.core.user import commands as user_commands
from udata.i18n import gettext as _
from udata.search.commands import index

from .db import migrate
from .fixtures import generate_fixtures

log = logging.getLogger(__name__)


@cli.command()
@click.pass_context
def init(ctx):
    '''Initialize your udata instance (search index, user, sample data...)'''

    log.info('Apply DB migrations if needed')
    ctx.invoke(migrate, record=True)

    if current_app.config['SEARCH_SERVICE_API_URL']:
        log.info('Preparing index')
        ctx.invoke(index)

    if IS_TTY:
        text = _('Do you want to create a superadmin user?')
        if click.confirm(text, default=True):
            user = ctx.invoke(user_commands.create)
            ctx.invoke(user_commands.set_admin, email=user.email)

        text = _('Do you want to import some data-related license?')
        if click.confirm(text, default=True):
            ctx.invoke(licenses)

        text = _('Do you want to import some spatial zones (countries)?')
        if click.confirm(text, default=True):
            ctx.invoke(spatial_load)

        text = _('Do you want to create some sample data?')
        if click.confirm(text, default=True):
            ctx.invoke(generate_fixtures)

    success(_('Your udata instance is ready!'))
