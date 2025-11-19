import collections
import os
from datetime import date, datetime
from tempfile import NamedTemporaryFile

from celery.utils.log import get_task_logger
from flask import current_app
from mongoengine import ValidationError

from udata import models as udata_models
from udata.core import csv, storages
from udata.core.badges import tasks as badge_tasks
from udata.core.constants import HVD
from udata.core.dataservices.models import Dataservice
from udata.core.dataset.constants import INSPIRE
from udata.core.organization.constants import CERTIFIED, PUBLIC_SERVICE
from udata.core.organization.models import Organization
from udata.core.pages.models import Page
from udata.harvest.models import HarvestJob
from udata.models import Activity, Discussion, Follow, TopicElement, Transfer, db
from udata.storage.s3 import store_bytes
from udata.tasks import job

from .models import Checksum, CommunityResource, Dataset, Resource

log = get_task_logger(__name__)


def flatten(iterable):
    for el in iterable:
        if isinstance(el, collections.Iterable) and not (
            isinstance(el, str) or isinstance(el, db.Document)
        ):
            yield from flatten(el)
        else:
            yield el


@job("purge-datasets")
def purge_datasets(self):
    for dataset in Dataset.objects(deleted__ne=None):
        log.info(f"Purging dataset {dataset}")
        # Remove followers
        Follow.objects(following=dataset).delete()
        # Remove discussions
        Discussion.objects(subject=dataset).delete()
        # Remove activity
        Activity.objects(related_to=dataset).delete()
        # Remove topics' related dataset
        TopicElement.objects(element=dataset).update(element=None)
        # Remove dataservices related dataset
        for dataservice in Dataservice.objects(datasets=dataset):
            datasets = dataservice.datasets
            datasets.remove(dataset)
            dataservice.update(datasets=datasets)
        # Remove HarvestItem references
        HarvestJob.objects(items__dataset=dataset).update(set__items__S__dataset=None)
        # Remove datasets in pages (mongoengine doesn't support updating a field in a generic embed)
        Page._get_collection().update_many(
            {"blocs.datasets": dataset.id},
            {"$pull": {"blocs.$[b].datasets": dataset.id}},
            array_filters=[{"b.datasets": dataset.id}],
        )
        # Remove associated Transfers
        Transfer.objects(subject=dataset).delete()
        # Remove each dataset's resource's file
        storage = storages.resources
        for resource in dataset.resources:
            if resource.fs_filename is not None:
                try:
                    storage.delete(resource.fs_filename)
                except FileNotFoundError as e:
                    log.warning(e)
            # Not removing the resource from dataset.resources
            # with `dataset.remove_resource` as removing elements
            # from a list while iterating causes random effects.
            Dataset.on_resource_removed.send(Dataset, document=dataset, resource_id=resource.id)
        # Remove each dataset related community resource and it's file
        community_resources = CommunityResource.objects(dataset=dataset)
        for community_resource in community_resources:
            if community_resource.fs_filename is not None:
                storage.delete(community_resource.fs_filename)
            community_resource.delete()
        # Remove dataset
        dataset.delete()


def get_queryset(model_cls):
    # special case for resources
    if model_cls.__name__ == "Resource":
        model_cls = getattr(udata_models, "Dataset")
    params = {}
    attrs = ("private", "deleted", "deleted_at")
    for attr in attrs:
        if getattr(model_cls, attr, None):
            params[attr] = False
    # no_cache to avoid eating up too much RAM
    return model_cls.objects.filter(**params).no_cache()


def get_resource_for_csv_export_model(model, dataset):
    for resource in dataset.resources:
        if resource.extras.get("csv-export:model", "") == model:
            return resource


def get_or_create_resource(r_info, model, dataset):
    resource = get_resource_for_csv_export_model(model, dataset)
    if resource:
        for k, v in r_info.items():
            setattr(resource, k, v)
        resource.save()
        return False, resource
    else:
        r_info["extras"] = {"csv-export:model": model}
        return True, Resource(**r_info)


def store_resource(csvfile, model, dataset):
    timestr = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    filename = "export-%s-%s.csv" % (model, timestr)
    prefix = "/".join((dataset.slug, timestr))
    storage = storages.resources
    with open(csvfile.name, "rb") as infile:
        stored_filename = storage.save(infile, prefix=prefix, filename=filename)
    r_info = storage.metadata(stored_filename)
    r_info["last_modified_internal"] = r_info.pop("modified")
    r_info["fs_filename"] = stored_filename
    checksum = r_info.pop("checksum")
    algo, checksum = checksum.split(":", 1)
    r_info["format"] = storages.utils.extension(stored_filename)
    r_info["checksum"] = Checksum(type=algo, value=checksum)
    r_info["filesize"] = r_info.pop("size")
    del r_info["filename"]
    r_info["title"] = filename
    return get_or_create_resource(r_info, model, dataset)


def export_csv_for_model(model, dataset, replace: bool = False):
    model_cls = getattr(udata_models, model.capitalize(), None)
    if not model_cls:
        log.error("Unknow model %s" % model)
        return

    fs_filename_to_remove = None
    if existing_resource := get_resource_for_csv_export_model(model, dataset):
        fs_filename_to_remove = existing_resource.fs_filename

    queryset = get_queryset(model_cls)
    adapter = csv.get_adapter(model_cls)
    if not adapter:
        log.error("No adapter found for %s" % model)
        return
    adapter = adapter(queryset)

    log.info("Exporting CSV for %s..." % model)

    csvfile = NamedTemporaryFile(mode="w", encoding="utf8", delete=False)
    try:
        # write adapter results into a tmp file
        writer = csv.get_writer(csvfile)
        writer.writerow(adapter.header())
        for row in adapter.rows():
            writer.writerow(row)
        csvfile.flush()
        # make a resource from this tmp file
        created, resource = store_resource(csvfile, model, dataset)
        # add it to the dataset
        if created:
            dataset.add_resource(resource)
        else:
            dataset.last_modified_internal = datetime.utcnow()
            dataset.save()
        # remove previous catalog if exists and replace is True
        if replace and fs_filename_to_remove:
            storages.resources.delete(fs_filename_to_remove)
        return resource
    finally:
        csvfile.close()
        os.unlink(csvfile.name)


@job("export-csv")
def export_csv(self, model=None):
    """
    Generates a CSV export of all model objects as a resource of a dataset
    """
    ALLOWED_MODELS = current_app.config.get("EXPORT_CSV_MODELS", [])
    DATASET_ID = current_app.config.get("EXPORT_CSV_DATASET_ID")

    if model and model not in ALLOWED_MODELS:
        log.error("Unknown or unallowed model: %s" % model)
        return

    if not DATASET_ID:
        log.error("EXPORT_CSV_DATASET_ID setting value not set")
        return
    try:
        dataset = Dataset.objects.get(id=DATASET_ID)
    except Dataset.DoesNotExist:
        log.error("EXPORT_CSV_DATASET_ID points to a non existent dataset")
        return

    models = (model,) if model else ALLOWED_MODELS
    for model in models:
        resource = export_csv_for_model(model, dataset, replace=True)

        # If we are the first day of the month, archive today catalogs
        if (
            current_app.config["EXPORT_CSV_ARCHIVE_S3_BUCKET"]
            and resource
            and date.today().day == 1
        ):
            log.info(
                f"Archiving {model} csv catalog on {current_app.config['EXPORT_CSV_ARCHIVE_S3_BUCKET']} bucket"
            )
            with storages.resources.open(resource.fs_filename, "rb") as f:
                store_bytes(
                    bucket=current_app.config["EXPORT_CSV_ARCHIVE_S3_BUCKET"],
                    filename=f"{current_app.config['EXPORT_CSV_ARCHIVE_S3_FILENAME_PREFIX']}{resource.title}",
                    bytes=f.read(),
                )


@job("bind-tabular-dataservice")
def bind_tabular_dataservice(self):
    """
    Bind the datasets served by TabularAPI to its dataservice objects
    """
    TABULAR_API_DATASERVICE_ID = current_app.config.get("TABULAR_API_DATASERVICE_ID", [])

    if not TABULAR_API_DATASERVICE_ID:
        log.error("TABULAR_API_DATASERVICE_ID setting value not set")
        return
    try:
        dataservice = Dataservice.objects.get(id=TABULAR_API_DATASERVICE_ID)
    except Dataservice.DoesNotExist:
        log.error("TABULAR_API_DATASERVICE_ID points to a non existent dataservice")
        return

    datasets = Dataset.objects(
        **{
            "resources__extras__analysis:parsing:finished_at__exists": True,
            "resources__extras__analysis:parsing:error": None,
        }
    ).visible()

    dataservice.datasets = datasets

    try:
        dataservice.save()
    except ValidationError as e:
        log.error(exc_info=e)

    log.info(f"Bound {datasets.count()} datasets to TabularAPI dataservice")


@badge_tasks.register(model=Dataset, badge=HVD)
def update_dataset_hvd_badge() -> None:
    """
    Update HVD badges to candidate datasets, based on the hvd tag.
    Only datasets owned by certified and public service organizations are candidate to have a HVD badge.
    """
    if not current_app.config["HVD_SUPPORT"]:
        log.error("You need to set HVD_SUPPORT if you want to update dataset hvd badge")
        return
    public_certified_orgs = (
        Organization.objects(badges__kind=PUBLIC_SERVICE).filter(badges__kind=CERTIFIED).only("id")
    )

    datasets = Dataset.objects(
        tags="hvd", badges__kind__ne="hvd", organization__in=public_certified_orgs
    )
    log.info(f"Adding HVD badge to {datasets.count()} datasets")
    for dataset in datasets:
        dataset.add_badge(HVD)

    datasets = Dataset.objects(tags__nin=["hvd"], badges__kind="hvd")
    log.info(f"Removing HVD badge from {datasets.count()} datasets")
    for dataset in datasets:
        dataset.remove_badge(HVD)


@badge_tasks.register(model=Dataset, badge=INSPIRE)
def update_dataset_inspire_badge() -> None:
    """
    Update INSPIRE badges to candidate datasets, based on the inspire tag.
    """
    if not current_app.config["INSPIRE_SUPPORT"]:
        log.error("You need to set INSPIRE_SUPPORT if you want to update dataset INSPIRE badge")
        return
    datasets = Dataset.objects(tags="inspire", badges__kind__ne="inspire")
    log.info(f"Adding INSPIRE badge to {datasets.count()} datasets")
    for dataset in datasets:
        dataset.add_badge(INSPIRE)

    datasets = Dataset.objects(tags__nin=["inspire"], badges__kind="inspire")
    log.info(f"Removing INSPIRE badge from {datasets.count()} datasets")
    for dataset in datasets:
        dataset.remove_badge(INSPIRE)
