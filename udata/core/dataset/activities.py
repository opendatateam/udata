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


class UserAddedResourceToDataset(DatasetRelatedActivity, Activity):
    key = "dataset:resource:added"
    icon = "fa fa-plus"
    label = _("added a resource to a dataset")


class UserUpdatedResource(DatasetRelatedActivity, Activity):
    key = "dataset:resource:updated"
    icon = "fa fa-pencil"
    label = _("updated a resource")


class UserRemovedResourceFromDataset(DatasetRelatedActivity, Activity):
    key = "dataset:resource:deleted"
    icon = "fa fa-remove"
    label = _("removed a resource from a dataset")


@Dataset.on_resource_added.connect
def on_user_added_resource_to_dataset(sender, document, **kwargs):
    if current_user and current_user.is_authenticated:
        UserAddedResourceToDataset.emit(
            document, document.organization, None, {"resource_id": str(kwargs["resource_id"])}
        )


@Dataset.on_resource_updated.connect
def on_user_updated_resource(sender, document, **kwargs):
    changed_fields = kwargs.get("changed_fields", [])
    if current_user and current_user.is_authenticated:
        UserUpdatedResource.emit(
            document,
            document.organization,
            changed_fields,
            {"resource_id": str(kwargs["resource_id"])},
        )


@Dataset.on_resource_removed.connect
def on_user_removed_resource_from_dataset(sender, document, **kwargs):
    if current_user and current_user.is_authenticated:
        UserRemovedResourceFromDataset.emit(
            document, document.organization, None, {"resource_id": str(kwargs["resource_id"])}
        )


@Dataset.on_create.connect
def on_user_created_dataset(dataset):
    if current_user and current_user.is_authenticated:
        UserCreatedDataset.emit(dataset, dataset.organization)


@Dataset.on_update.connect
def on_user_updated_dataset(dataset, **kwargs):
    changed_fields = kwargs.get("changed_fields", [])
    if current_user and current_user.is_authenticated:
        UserUpdatedDataset.emit(dataset, dataset.organization, changed_fields)


@Dataset.on_delete.connect
def on_user_deleted_dataset(dataset):
    if current_user and current_user.is_authenticated:
        UserDeletedDataset.emit(dataset, dataset.organization)
