import csv
import logging
from collections import namedtuple
from datetime import datetime, timedelta

from bson import ObjectId
from flask import current_app

from udata.auth import current_user
from udata.core.dataset.models import HarvestDatasetMetadata
from udata.models import Dataset, Organization, PeriodicTask, User
from udata.storage.s3 import delete_file

from . import backends, signals
from .models import (
    DEFAULT_HARVEST_FREQUENCY,
    VALIDATION_ACCEPTED,
    VALIDATION_REFUSED,
    HarvestJob,
    HarvestSource,
    archive_harvested_dataset,
)
from .tasks import harvest

log = logging.getLogger(__name__)

DEFAULT_PAGE_SIZE = 10


def list_backends():
    """List all available backends"""
    return backends.get_all(current_app).values()


def _sources_queryset(owner=None, deleted=False):
    sources = HarvestSource.objects
    if not deleted:
        sources = sources.visible()
    if owner:
        sources = sources.owned_by(owner)
    return sources


def list_sources(owner=None, deleted=False):
    """List all harvest sources"""
    return list(_sources_queryset(owner=owner, deleted=deleted))


def paginate_sources(owner=None, page=1, page_size=DEFAULT_PAGE_SIZE, deleted=False):
    """Paginate harvest sources"""
    sources = _sources_queryset(owner=owner, deleted=deleted)
    page = max(page or 1, 1)
    return sources.paginate(page, page_size)


def get_source(ident):
    """Get an harvest source given its ID or its slug"""
    return HarvestSource.get(ident)


def get_job(ident):
    """Get an harvest job given its ID"""
    return HarvestJob.objects.get(id=ident)


def create_source(
    name,
    url,
    backend,
    description=None,
    frequency=DEFAULT_HARVEST_FREQUENCY,
    owner=None,
    organization=None,
    config=None,
    active=None,
    autoarchive=None,
):
    """Create a new harvest source"""
    if owner and not isinstance(owner, User):
        owner = User.get(owner)

    if organization and not isinstance(organization, Organization):
        organization = Organization.get(organization)

    source = HarvestSource.objects.create(
        name=name,
        url=url,
        backend=backend,
        description=description,
        frequency=frequency or DEFAULT_HARVEST_FREQUENCY,
        owner=owner,
        organization=organization,
        config=config,
        active=active,
        autoarchive=autoarchive,
    )
    signals.harvest_source_created.send(source)
    return source


def update_source(ident, data):
    """Update an harvest source"""
    source = get_source(ident)
    source.modify(**data)
    signals.harvest_source_updated.send(source)
    return source


def validate_source(ident, comment=None):
    """Validate a source for automatic harvesting"""
    source = get_source(ident)
    source.validation.on = datetime.utcnow()
    source.validation.comment = comment
    source.validation.state = VALIDATION_ACCEPTED
    if current_user.is_authenticated:
        source.validation.by = current_user._get_current_object()
    source.save()
    schedule(ident, cron=current_app.config["HARVEST_DEFAULT_SCHEDULE"])
    launch(ident)
    return source


def reject_source(ident, comment):
    """Reject a source for automatic harvesting"""
    source = get_source(ident)
    source.validation.on = datetime.utcnow()
    source.validation.comment = comment
    source.validation.state = VALIDATION_REFUSED
    if current_user.is_authenticated:
        source.validation.by = current_user._get_current_object()
    source.save()
    return source


def delete_source(ident):
    """Delete an harvest source"""
    source = get_source(ident)
    source.deleted = datetime.utcnow()
    source.save()
    signals.harvest_source_deleted.send(source)
    return source


def clean_source(ident):
    """Deletes all datasets linked to a harvest source"""
    source = get_source(ident)
    datasets = Dataset.objects.filter(harvest__source_id=str(source.id))
    for dataset in datasets:
        dataset.deleted = datetime.utcnow()
        dataset.save()
    return len(datasets)


def purge_sources():
    """Permanently remove sources flagged as deleted"""
    sources = HarvestSource.objects(deleted__exists=True)
    count = sources.count()
    for source in sources:
        if source.periodic_task:
            source.periodic_task.delete()
        datasets = Dataset.objects.filter(harvest__source_id=str(source.id))
        for dataset in datasets:
            archive_harvested_dataset(dataset, reason="harvester-deleted", dryrun=False)
        source.delete()
    return count


def purge_jobs():
    """Delete jobs older than retention policy"""
    retention = current_app.config["HARVEST_JOBS_RETENTION_DAYS"]
    expiration = datetime.utcnow() - timedelta(days=retention)

    jobs_with_external_files = HarvestJob.objects(
        data__filename__exists=True, created__lt=expiration
    )
    for job in jobs_with_external_files:
        bucket = current_app.config.get("HARVEST_GRAPHS_S3_BUCKET")
        if bucket is None:
            log.error(
                "Bucket isn't configured anymore, but jobs still exist with external filenames. Could not delete them."
            )
            break

        delete_file(bucket, job.data["filename"])

    return HarvestJob.objects(created__lt=expiration).delete()


def run(ident):
    """Launch or resume an harvesting for a given source if none is running"""
    source = get_source(ident)
    cls = backends.get(current_app, source.backend)
    backend = cls(source)
    backend.harvest()


def launch(ident):
    """Launch or resume an harvesting for a given source if none is running"""
    return harvest.delay(ident)


def preview(ident):
    """Preview an harvesting for a given source"""
    source = get_source(ident)
    cls = backends.get(current_app, source.backend)
    max_items = current_app.config["HARVEST_PREVIEW_MAX_ITEMS"]
    backend = cls(source, dryrun=True, max_items=max_items)
    return backend.harvest()


def preview_from_config(
    name,
    url,
    backend,
    description=None,
    frequency=DEFAULT_HARVEST_FREQUENCY,
    owner=None,
    organization=None,
    config=None,
    active=None,
    autoarchive=None,
):
    """Preview an harvesting from a source created with the given parameters"""
    if owner and not isinstance(owner, User):
        owner = User.get(owner)

    if organization and not isinstance(organization, Organization):
        organization = Organization.get(organization)

    source = HarvestSource(
        name=name,
        url=url,
        backend=backend,
        description=description,
        frequency=frequency or DEFAULT_HARVEST_FREQUENCY,
        owner=owner,
        organization=organization,
        config=config,
        active=active,
        autoarchive=autoarchive,
    )
    cls = backends.get(current_app, source.backend)
    max_items = current_app.config["HARVEST_PREVIEW_MAX_ITEMS"]
    backend = cls(source, dryrun=True, max_items=max_items)
    return backend.harvest()


def schedule(
    ident, cron=None, minute="*", hour="*", day_of_week="*", day_of_month="*", month_of_year="*"
):
    """Schedule an harvesting on a source given a crontab"""
    source = get_source(ident)

    if cron:
        minute, hour, day_of_month, month_of_year, day_of_week = cron.split()

    crontab = PeriodicTask.Crontab(
        minute=str(minute),
        hour=str(hour),
        day_of_week=str(day_of_week),
        day_of_month=str(day_of_month),
        month_of_year=str(month_of_year),
    )

    if source.periodic_task:
        source.periodic_task.modify(crontab=crontab)
    else:
        source.modify(
            periodic_task=PeriodicTask.objects.create(
                task="harvest",
                name="Harvest {0}".format(source.name),
                description="Periodic Harvesting",
                enabled=True,
                args=[str(source.id)],
                crontab=crontab,
            )
        )
    signals.harvest_source_scheduled.send(source)
    return source


def unschedule(ident):
    """Unschedule an harvesting on a source"""
    source = get_source(ident)
    if not source.periodic_task:
        msg = "Harvesting on source {0} is ot scheduled".format(source.name)
        raise ValueError(msg)

    source.periodic_task.delete()
    signals.harvest_source_unscheduled.send(source)
    return source


AttachResult = namedtuple("AttachResult", ["success", "errors"])


def attach(domain, filename):
    """Attach existing dataset to their harvest remote id before harvesting.

    The expected csv file format is the following:

    - a column with header "local" and the local IDs or slugs
    - a column with header "remote" and the remote IDs

    The delimiter should be ";". columns order
    and extras columns does not matter
    """
    count = 0
    errors = 0
    with open(filename) as csvfile:
        reader = csv.DictReader(csvfile, delimiter=";", quotechar='"')
        for row in reader:
            try:
                dataset = Dataset.objects.get(id=ObjectId(row["local"]))
            except:  # noqa  (Never stop on failure)
                log.warning("Unable to attach dataset : %s", row["local"])
                errors += 1
                continue

            # Detach previously attached dataset
            Dataset.objects(
                **{"harvest__domain": domain, "harvest__remote_id": row["remote"]}
            ).update(**{"unset__harvest__domain": True, "unset__harvest__remote_id": True})

            if not dataset.harvest:
                dataset.harvest = HarvestDatasetMetadata()
            dataset.harvest.domain = domain
            dataset.harvest.remote_id = row["remote"]

            dataset.last_modified_internal = datetime.utcnow()
            dataset.save()
            count += 1

    return AttachResult(count, errors)
