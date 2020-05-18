from udata.models import db, Dataset, Reuse, Organization


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


@db.Owned.on_owner_change.connect
def update_org_metrics(document, previous):
    if not isinstance(previous, Organization):
        return
    if isinstance(document, Dataset):
        previous.count_datasets()
    elif isinstance(document, Reuse):
        previous.count_reuses()
