from udata.core.dataservices.models import Dataservice
from udata.core.owned import Owned
from udata.models import Dataset, Organization, Reuse


@Dataset.on_create.connect
@Dataset.on_update.connect
@Dataset.on_delete.connect
def update_datasets_metrics(document, **kwargs):
    compute_aggregates = kwargs.get("compute_aggregates", True)
    if document.organization:
        document.organization.count_datasets(compute_aggregates=compute_aggregates)


@Reuse.on_create.connect
@Reuse.on_update.connect
@Reuse.on_delete.connect
def update_reuses_metrics(document, **kwargs):
    if document.organization:
        document.organization.count_reuses()


@Dataservice.on_create.connect
@Dataservice.on_update.connect
@Dataservice.on_delete.connect
def update_dataservices_metrics(document, **kwargs):
    if document.organization:
        document.organization.count_dataservices()


@Owned.on_owner_change.connect
def update_org_metrics(document, previous):
    if not isinstance(previous, Organization):
        return
    if isinstance(document, Dataset):
        previous.count_datasets()
    elif isinstance(document, Reuse):
        previous.count_reuses()
