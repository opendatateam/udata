import collections
import os
from datetime import datetime, timedelta
from tempfile import NamedTemporaryFile

from celery.utils.log import get_task_logger
from flask import current_app

from udata import mail
from udata import models as udata_models
from udata.core import storages
from udata.frontend import csv
from udata.harvest.models import HarvestJob
from udata.i18n import lazy_gettext as _
from udata.models import Activity, Discussion, Follow, Organization, Topic, Transfer, db
from udata.tasks import job

from .constants import UPDATE_FREQUENCIES
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
        for topic in Topic.objects(datasets=dataset):
            datasets = topic.datasets
            datasets.remove(dataset)
            topic.update(datasets=datasets)
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


@job("send-frequency-reminder")
def send_frequency_reminder(self):
    # We exclude irrelevant frequencies.
    frequencies = [
        f
        for f in UPDATE_FREQUENCIES.keys()
        if f not in ("unknown", "realtime", "punctual", "irregular", "continuous")
    ]
    now = datetime.utcnow()
    reminded_orgs = {}
    reminded_people = []
    allowed_delay = current_app.config["DELAY_BEFORE_REMINDER_NOTIFICATION"]
    for org in Organization.objects.visible():
        outdated_datasets = []
        for dataset in Dataset.objects.filter(
            frequency__in=frequencies, organization=org
        ).visible():
            if dataset.next_update + timedelta(days=allowed_delay) < now:
                dataset.outdated = now - dataset.next_update
                dataset.frequency_str = UPDATE_FREQUENCIES[dataset.frequency]
                outdated_datasets.append(dataset)
        if outdated_datasets:
            reminded_orgs[org] = outdated_datasets
    for reminded_org, datasets in reminded_orgs.items():
        print(
            "{org.name} will be emailed for {datasets_nb} datasets".format(
                org=reminded_org, datasets_nb=len(datasets)
            )
        )
        recipients = [m.user for m in reminded_org.members]
        reminded_people.append(recipients)
        subject = _("You need to update some frequency-based datasets")
        mail.send(subject, recipients, "frequency_reminder", org=reminded_org, datasets=datasets)

    print("{nb_orgs} orgs concerned".format(nb_orgs=len(reminded_orgs)))
    reminded_people = list(flatten(reminded_people))
    print(
        "{nb_emails} people contacted ({nb_emails_twice} twice)".format(
            nb_emails=len(reminded_people),
            nb_emails_twice=len(reminded_people) - len(set(reminded_people)),
        )
    )
    print("Done")


@job("update-datasets-reuses-metrics")
def update_datasets_reuses_metrics(self):
    all_datasets = Dataset.objects.visible().timeout(False)
    for dataset in all_datasets:
        dataset.count_reuses()


def get_queryset(model_cls):
    # special case for resources
    if model_cls.__name__ == "Resource":
        model_cls = getattr(udata_models, "Dataset")
    params = {}
    attrs = ("private", "deleted")
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
