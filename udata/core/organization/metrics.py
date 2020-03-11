from udata.models import Dataset, Reuse


@Dataset.on_create.connect
@Dataset.on_update.connect
@Dataset.on_delete.connect
def update_datasets_metrics(document, **kwargs):
    if document.organization:
        document.organization.count_datasets()


@Reuse.on_create.connect
@Reuse.on_update.connect
@Reuse.on_delete.connect
def update_reuses_metrics(document, **kwargs):
    if document.organization:
        document.organization.count_reuses()