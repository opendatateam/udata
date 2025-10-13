import collections
import os
from datetime import datetime
from tempfile import NamedTemporaryFile

from celery.utils.log import get_task_logger
from flask import current_app
from mongoengine import ValidationError

from udata import models as udata_models
from udata.core import csv, storages
from udata.core.dataservices.models import Dataservice
from udata.harvest.models import HarvestJob
from udata.models import Activity, Discussion, Follow, TopicElement, Transfer, db
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


def get_or_create_resource(r_info, model, dataset):
    resource = None
    for r in dataset.resources:
        if r.extras.get("csv-export:model", "") == model:
            resource = r
            break
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


def export_csv_for_model(model, dataset):
    model_cls = getattr(udata_models, model.capitalize(), None)
    if not model_cls:
        log.error("Unknow model %s" % model)
        return
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
        export_csv_for_model(model, dataset)


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
