from udata.core.followers.metrics import FollowersMetric
from udata.models import Dataset, Reuse, Organization


@Dataset.on_create.connect
@Dataset.on_delete.connect
def update_datasets_metrics(document, **kwargs):
    if document.organization:
        document.organization.datasets_count()
        document.organization.save()


@Reuse.on_create.connect
@Reuse.on_delete.connect
def update_reuses_metrics(document, **kwargs):
    if document.organization:
        document.organization.reuses_count()
        document.organization.save()


@Reuse.on_create.connect
@Reuse.on_delete.connect
def update_followers_metrics(document, **kwargs):
    document.followers_count()
    document.save()