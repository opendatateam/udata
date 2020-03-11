import click
import logging

from os.path import exists

from udata.commands import cli
from udata.models import Organization

log = logging.getLogger(__name__)


@cli.group('badges')
def grp():
    '''Badges related operations'''


def toggle_badge(id_or_slug, badge_kind):
    organization = Organization.objects.get_by_id_or_slug(id_or_slug)
    if not organization:
        log.error('No organization found for %s', id_or_slug)
        return
    log.info('Toggling badge {kind} for organization {org}'.format(
        kind=badge_kind,
        org=organization.name
    ))
    organization.toggle_badge(badge_kind)


@grp.command()
@click.argument('path_or_id')
@click.argument('badge_kind')
def toggle(path_or_id, badge_kind):
    '''Toggle a `badge_kind` for a given `path_or_id`

    The `path_or_id` is either an id, a slug or a file containing a list
    of ids or slugs.
    '''
    if exists(path_or_id):
        with open(path_or_id) as open_file:
            for id_or_slug in open_file.readlines():
                toggle_badge(id_or_slug.strip(), badge_kind)
    else:
        toggle_badge(path_or_id, badge_kind)
