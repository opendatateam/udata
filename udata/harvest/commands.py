import logging

import click

from udata.commands import KO, OK, cli, green, red
from udata.harvest.backends import get_all_backends, is_backend_enabled
from udata.models import Dataset

from . import actions

log = logging.getLogger(__name__)


@cli.group("harvest")
def grp():
    """Remote repositories harvesting operations"""
    pass


@grp.command()
@click.argument("backend")
@click.argument("url")
@click.argument("name")
@click.option("-f", "--frequency", default=None)
@click.option("-u", "--owner", default=None)
@click.option("-o", "--org", default=None)
def create(name, url, backend, frequency=None, owner=None, org=None):
    """Create a new harvest source"""
    log.info('Creating a new Harvest source "%s"', name)
    source = actions.create_source(
        name, url, backend, frequency=frequency, owner=owner, organization=org
    )
    log.info(
        """Created a new Harvest source:
    name: {0.name},
    slug: {0.slug},
    url: {0.url},
    backend: {0.backend},
    frequency: {0.frequency},
    owner: {0.owner},
    organization: {0.organization}""".format(source)
    )


@grp.command()
@click.argument("identifier")
def validate(identifier):
    """Validate a source given its identifier"""
    source = actions.validate_source(actions.get_source(identifier))
    log.info("Source %s (%s) has been validated", source.slug, str(source.id))


@grp.command()
def delete(identifier):
    """Delete a harvest source"""
    log.info('Deleting source "%s"', identifier)
    actions.delete_source(actions.get_source(identifier))
    log.info('Deleted source "%s"', identifier)


@grp.command()
@click.argument("identifier")
def clean(identifier):
    """Delete all datasets linked to a harvest source"""
    log.info(f'Cleaning source "{identifier}"')
    num_of_datasets = actions.clean_source(actions.get_source(identifier))
    log.info(f'Cleaned source "{identifier}" - deleted {num_of_datasets} dataset(s)')


@grp.command()
@click.option("-s", "--scheduled", is_flag=True, help="list only scheduled source")
def sources(scheduled=False):
    """List all harvest sources"""
    sources = actions.list_sources()
    if scheduled:
        sources = [s for s in sources if s.periodic_task]
    if sources:
        for source in sources:
            msg = "{source.name} ({source.backend}): {cron}"
            if source.periodic_task:
                cron = source.periodic_task.schedule_display
            else:
                cron = "not scheduled"
            log.info(msg.format(source=source, cron=cron))
    elif scheduled:
        log.info("No sources scheduled yet")
    else:
        log.info("No sources defined yet")


@grp.command()
def backends():
    """List available backends"""
    print("Available backends:")
    for backend in get_all_backends().values():
        status = green(OK) if is_backend_enabled(backend) else red(KO)
        click.echo("{0} {1} ({2})".format(status, backend.display_name, backend.name))


@grp.command()
@click.argument("identifier")
def launch(identifier):
    """Launch a source harvesting on the workers"""
    log.info('Launching harvest job for source "%s"', identifier)
    actions.launch(actions.get_source(identifier))


@grp.command()
@click.argument("identifier")
def run(identifier):
    """Run a harvester synchronously"""
    log.info('Harvesting source "%s"', identifier)
    actions.run(actions.get_source(identifier))


@grp.command()
@click.argument("identifier")
@click.option("-m", "--minute", default="*", help="The crontab expression for minute")
@click.option("-h", "--hour", default="*", help="The crontab expression for hour")
@click.option(
    "-d", "--day", "day_of_week", default="*", help="The crontab expression for day of week"
)
@click.option("-D", "--day-of-month", default="*", help="The crontab expression for day of month")
@click.option("-M", "--month-of-year", default="*", help="The crontab expression for month of year")
def schedule(identifier, **kwargs):
    """Schedule a harvest job to run periodically"""
    source = actions.schedule(actions.get_source(identifier), **kwargs)
    msg = "Scheduled {source.name} with the following crontab: {cron}"
    log.info(msg.format(source=source, cron=source.periodic_task.crontab))


@grp.command()
@click.argument("identifier")
def unschedule(identifier):
    """Unschedule a periodical harvest job"""
    source = actions.unschedule(actions.get_source(identifier))
    log.info('Unscheduled harvest source "%s"', source.name)


@grp.command()
def purge():
    """Permanently remove deleted harvest sources"""
    log.info("Purging deleted harvest sources")
    count = actions.purge_sources()
    log.info("Purged %s source(s)", count)


@grp.command()
@click.argument("filename")
@click.argument("domain")
def attach(domain, filename):
    """
    Attach existing datasets to their harvest remote id

    Mapping between identifiers should be in FILENAME CSV file.
    """
    log.info("Attaching datasets for domain %s", domain)
    result = actions.attach(domain, filename)
    log.info("Attached %s datasets to %s", result.success, domain)


@grp.command()
@click.argument("dataset_id")
def detach(dataset_id):
    """
    Detach a dataset_id from its harvest source

    The dataset will be cleaned from harvested information
    """
    log.info(f"Detaching dataset {dataset_id}")
    dataset = Dataset.get(dataset_id)
    actions.detach(dataset)
    log.info("Done")


@grp.command()
@click.argument("identifier")
def detach_all_from_source(identifier):
    """
    Detach all datasets from a harvest source

    All the datasets will be cleaned from harvested information.
    Make sure the harvest source won't create new duplicate datasets,
    either by deactivating it or filtering its scope, etc.
    """
    log.info(f"Detaching datasets from harvest source {identifier}")
    count = actions.detach_all_from_source(actions.get_source(identifier))
    log.info(f"Detached {count} datasets")
    log.warning(
        "Make sure the harvest source won't create new duplicate datasets, either by deactivating it or filtering its scope, etc."
    )
