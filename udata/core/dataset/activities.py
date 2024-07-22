from udata.auth import current_user
from udata.i18n import lazy_gettext as _
from udata.models import Activity, Dataset, db

__all__ = (
    "UserCreatedDataset",
    "UserUpdatedDataset",
    "UserDeletedDataset",
    "DatasetRelatedActivity",
)


class DatasetRelatedActivity(object):
    template = "activity/dataset.html"
    related_to = db.ReferenceField("Dataset")


class UserCreatedDataset(DatasetRelatedActivity, Activity):
    key = "dataset:created"
    icon = "fa fa-plus"
    badge_type = "success"
    label = _("created a dataset")


class UserUpdatedDataset(DatasetRelatedActivity, Activity):
    key = "dataset:updated"
    icon = "fa fa-pencil"
    label = _("updated a dataset")


class UserDeletedDataset(DatasetRelatedActivity, Activity):
    key = "dataset:deleted"
    icon = "fa fa-remove"
    badge_type = "error"
    label = _("deleted a dataset")


@Dataset.on_create.connect
def on_user_created_dataset(dataset):
    if not dataset.private and current_user and current_user.is_authenticated:
        UserCreatedDataset.emit(dataset, dataset.organization)


@Dataset.on_update.connect
def on_user_updated_dataset(dataset):
    if not dataset.private and current_user and current_user.is_authenticated:
        UserUpdatedDataset.emit(dataset, dataset.organization)


@Dataset.on_delete.connect
def on_user_deleted_dataset(dataset):
    if not dataset.private and current_user and current_user.is_authenticated:
        UserDeletedDataset.emit(dataset, dataset.organization)
