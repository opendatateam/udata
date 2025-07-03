from udata.auth import current_user
from udata.i18n import lazy_gettext as _
from udata.models import Activity, Dataservice, db

__all__ = (
    "UserCreatedDataservice",
    "UserUpdatedDataservice",
    "UserDeletedDataservice",
    "DataserviceRelatedActivity",
)


class DataserviceRelatedActivity(object):
    related_to = db.ReferenceField("Dataservice")


class UserCreatedDataservice(DataserviceRelatedActivity, Activity):
    key = "dataservice:created"
    icon = "fa fa-plus"
    badge_type = "success"
    label = _("created a dataservice")


class UserUpdatedDataservice(DataserviceRelatedActivity, Activity):
    key = "dataservice:updated"
    icon = "fa fa-pencil"
    label = _("updated a dataservice")


class UserDeletedDataservice(DataserviceRelatedActivity, Activity):
    key = "dataservice:deleted"
    icon = "fa fa-remove"
    badge_type = "error"
    label = _("deleted a dataservice")


@Dataservice.on_create.connect
def on_user_created_dataservice(dataservice):
    if current_user and current_user.is_authenticated:
        UserCreatedDataservice.emit(dataservice, dataservice.organization)


@Dataservice.on_update.connect
def on_user_updated_dataservice(dataservice, **kwargs):
    changed_fields = kwargs.get("changed_fields", [])
    if current_user and current_user.is_authenticated:
        UserUpdatedDataservice.emit(dataservice, dataservice.organization, changed_fields)


@Dataservice.on_delete.connect
def on_user_deleted_dataservice(dataservice):
    if current_user and current_user.is_authenticated:
        UserDeletedDataservice.emit(dataservice, dataservice.organization)
