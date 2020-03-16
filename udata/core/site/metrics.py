from udata.models import Dataset, Reuse, User, Resource
from udata.core.followers.signals import on_follow, on_unfollow

from .views import current_site


@Dataset.on_create.connect
@Dataset.on_update.connect
@Dataset.on_delete.connect
def update_datasets_metrics(document, **kwargs):
    current_site.count_datasets()
    current_site.count_max_dataset_reuses()
    current_site.count_max_org_datasets()
    current_site.count_resources()


@Reuse.on_create.connect
@Reuse.on_update.connect
@Reuse.on_delete.connect
def update_reuses_metrics(document, **kwargs):
    current_site.count_reuses()
    current_site.count_max_reuse_datasets()
    current_site.count_max_org_reuses()


@Dataset.on_update.connect
@Resource.on_added.connect
@Resource.on_deleted.connect
def update_ressources_metrics(document, **kwargs):
    current_site.count_resources()


@User.on_create.connect
@User.on_update.connect
@User.on_delete.connect
def update_users_metrics(document, **kwargs):
    current_site.count_users()


@on_follow.connect
@on_unfollow.connect
def update_followers_metrics(document, **kwargs):
    current_site.count_followers()
    current_site.count_max_dataset_followers()
    current_site.count_max_reuse_followers()
    current_site.count_max_org_followers()
