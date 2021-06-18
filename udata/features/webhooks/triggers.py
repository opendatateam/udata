from udata.features.webhooks.tasks import dispatch
from udata.models import Dataset


@Dataset.on_create.connect
def on_dataset_created(dataset):
    # TODO: emit a private signal somehow (or just rename it to draft)
    dispatch('datagouvfr.dataset.created', dataset.to_json())
