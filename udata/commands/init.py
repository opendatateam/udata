import logging

import click
from flask import current_app

from udata.commands import IS_TTY, cli, success
from udata.core.dataset.commands import licenses
from udata.core.spatial.commands import load as spatial_load
from udata.core.user import commands as user_commands
from udata.i18n import gettext as _
from udata.search.commands import index

from .db import migrate
from .fixtures import import_fixtures

log = logging.getLogger(__name__)


@cli.command()
@click.pass_context
@click.option("--admin-email")
@click.option("--admin-password")
@click.option("--admin-first-name")
@click.option("--admin-last-name")
@click.option("--create-admin/--no-create-admin", default=None)
@click.option("--import-licenses/--no-import-licenses", default=None)
@click.option("--import-spatial/--no-import-spatial", default=None)
@click.option("--import-fixtures/--no-import-fixtures", default=None)
def init(ctx, admin_email, admin_password, admin_first_name, admin_last_name, 
         create_admin, import_licenses, import_spatial, import_fixtures):
    """Initialize your udata instance (search index, user, sample data...)"""

    log.info("Apply DB migrations if needed")
    ctx.invoke(migrate, record=True)

    if current_app.config["SEARCH_SERVICE_API_URL"]:
        log.info("Preparing index")
        ctx.invoke(index)

    should_create_admin = create_admin
    should_import_licenses = import_licenses
    should_import_spatial = import_spatial
    should_import_fixtures = import_fixtures

    if IS_TTY:
        if should_create_admin is None:
            text = _("Do you want to create a superadmin user?")
            should_create_admin = click.confirm(text, default=True)
        
        if should_import_licenses is None:
            text = _("Do you want to import some data-related license?")
            should_import_licenses = click.confirm(text, default=True)

        if should_import_spatial is None:
            text = _("Do you want to import some spatial zones (countries)?")
            should_import_spatial = click.confirm(text, default=True)

        if should_import_fixtures is None:
            text = _("Do you want to create some sample data?")
            should_import_fixtures = click.confirm(text, default=True)

    if should_create_admin:
        if admin_email and admin_password:
            user = ctx.invoke(user_commands.create, 
                            first_name=admin_first_name,
                            last_name=admin_last_name,
                            email=admin_email, 
                            password=admin_password)
        else:
            user = ctx.invoke(user_commands.create)
        ctx.invoke(user_commands.set_admin, email=user.email)

    if should_import_licenses:
        ctx.invoke(licenses)

    if should_import_spatial:
        ctx.invoke(spatial_load)

    if should_import_fixtures:
        ctx.invoke(import_fixtures)

    success(_("Your udata instance is ready!"))
