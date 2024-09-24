import os
from datetime import datetime
from tempfile import NamedTemporaryFile

from flask import current_app

from udata import mail
from udata import models as udata_models
from udata.core import storages
from udata.core.dataset.models import Dataset
from udata.core.post.models import Post
from udata.core.reuse.models import Reuse
from udata.frontend import csv
from udata.i18n import lazy_gettext as _
from udata.tasks import connect, get_logger, job

from .models import Discussion, Resource, Checksum
from .signals import on_discussion_closed, on_new_discussion, on_new_discussion_comment

log = get_logger(__name__)


def owner_recipients(discussion):
    if getattr(discussion.subject, "organization", None):
        return [m.user for m in discussion.subject.organization.members]
    elif getattr(discussion.subject, "owner", None):
        return [discussion.subject.owner]
    else:
        return []


@connect(on_new_discussion, by_id=True)
def notify_new_discussion(discussion_id):
    discussion = Discussion.objects.get(pk=discussion_id)
    if isinstance(discussion.subject, (Dataset, Reuse, Post)):
        recipients = owner_recipients(discussion)
        subject = _("Your %(type)s have a new discussion", type=discussion.subject.verbose_name)
        mail.send(
            subject,
            recipients,
            "new_discussion",
            discussion=discussion,
            message=discussion.discussion[0],
        )
    else:
        log.warning("Unrecognized discussion subject type %s", type(discussion.subject))


@connect(on_new_discussion_comment, by_id=True)
def notify_new_discussion_comment(discussion_id, message=None):
    discussion = Discussion.objects.get(pk=discussion_id)
    message = discussion.discussion[message]
    if isinstance(discussion.subject, (Dataset, Reuse, Post)):
        recipients = owner_recipients(discussion) + [m.posted_by for m in discussion.discussion]
        recipients = list({u.id: u for u in recipients if u != message.posted_by}.values())
        subject = _("%(user)s commented your discussion", user=message.posted_by.fullname)

        mail.send(
            subject, recipients, "new_discussion_comment", discussion=discussion, message=message
        )
    else:
        log.warning("Unrecognized discussion subject type %s", type(discussion.subject))


@connect(on_discussion_closed, by_id=True)
def notify_discussion_closed(discussion_id, message=None):
    discussion = Discussion.objects.get(pk=discussion_id)
    message = discussion.discussion[message]
    if isinstance(discussion.subject, (Dataset, Reuse, Post)):
        recipients = owner_recipients(discussion) + [m.posted_by for m in discussion.discussion]
        recipients = list({u.id: u for u in recipients if u != message.posted_by}.values())
        subject = _("A discussion has been closed")
        mail.send(subject, recipients, "discussion_closed", discussion=discussion, message=message)
    else:
        log.warning("Unrecognized discussion subject type %s", type(discussion.subject))


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
