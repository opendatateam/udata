import logging

import click

from udata.commands import cli, exit_with_error
from udata.models import GeoZone, Organization

log = logging.getLogger(__name__)


@cli.group("organizations")
def grp():
    """Organizations related operations"""


@grp.command()
@click.argument("geoid", metavar="<geoid>")
@click.argument("organization_id_or_slug", metavar="<organization>")
def attach_zone(geoid, organization_id_or_slug):
    """Attach a zone <geoid> restricted to level for a given <organization>."""
    organization = Organization.objects.get_by_id_or_slug(organization_id_or_slug)
    if not organization:
        log.error("No organization found for %s", organization_id_or_slug)
    geozone = GeoZone.objects.get(id=geoid)
    if not geozone:
        log.error("No geozone found for %s", geoid)
    log.info(f"Attaching {organization} with {geozone.name}")
    organization.zone = geozone.id
    organization.save()
    log.info("Done")


@grp.command()
@click.argument("organization_id_or_slug", metavar="<organization>")
def detach_zone(organization_id_or_slug):
    """Detach the zone of a given <organization>."""
    organization = Organization.objects.get_by_id_or_slug(organization_id_or_slug)
    if not organization:
        exit_with_error(f"No organization found for {organization_id_or_slug}")
    log.info(f"Detaching {organization} from {organization.zone}")
    organization.zone = None
    organization.save()
    log.info("Done")
