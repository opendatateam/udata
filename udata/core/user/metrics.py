from udata.core.followers.signals import on_follow, on_unfollow
from udata.core.owned import Owned
from udata.models import Dataset, Reuse, User


@Dataset.on_create.connect
@Dataset.on_update.connect
@Dataset.on_delete.connect
def update_datasets_metrics(document, **kwargs):
    if document.owner:
        document.owner.count_datasets()


@Reuse.on_create.connect
@Reuse.on_update.connect
@Reuse.on_delete.connect
def update_reuses_metrics(document, **kwargs):
    if document.owner:
        document.owner.count_reuses()


@on_follow.connect
@on_unfollow.connect
def update_user_following_metric(follow):
    follow.follower.count_following()


@Owned.on_owner_change.connect
def update_owner_metrics(document, previous):
    if not isinstance(previous, User):
        return
    if isinstance(document, Dataset):
        previous.count_datasets()
    elif isinstance(document, Reuse):
        previous.count_reuses()
