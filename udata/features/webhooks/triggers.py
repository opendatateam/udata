from udata.core.discussions.signals import (
    on_new_discussion, on_new_discussion_comment, on_discussion_closed,
    on_discussion_deleted
)

from udata.features.webhooks.tasks import dispatch
from udata.models import Dataset


@Dataset.on_create.connect
def on_dataset_create(dataset):
    # TODO: emit a private signal somehow (or just rename it to draft)
    dispatch('datagouvfr.dataset.created', dataset.to_json())


@Dataset.on_delete.connect
def on_dataset_delete(dataset):
    dispatch('datagouvfr.dataset.deleted', dataset.to_json())


@Dataset.on_update.connect
def on_dataset_update(dataset):
    dispatch('datagouvfr.dataset.updated', dataset.to_json())


@on_new_discussion.connect
def on_new_discussion(discussion):
    dispatch('datagouvfr.discussion.created', discussion.to_json())
