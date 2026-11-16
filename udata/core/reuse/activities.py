from mongoengine.fields import ReferenceField

from udata.i18n import lazy_gettext as _
from udata.models import Activity, Reuse

__all__ = ("UserCreatedReuse", "UserUpdatedReuse", "UserDeletedReuse", "ReuseRelatedActivity")


class ReuseRelatedActivity(object):
    template = "activity/reuse.html"
    related_to = ReferenceField("Reuse")


class UserCreatedReuse(ReuseRelatedActivity, Activity):
    key = "reuse:created"
    icon = "fa fa-plus"
    badge_type = "success"
    label = _("created a reuse")


class UserUpdatedReuse(ReuseRelatedActivity, Activity):
    key = "reuse:updated"
    icon = "fa fa-pencil"
    label = _("updated a reuse")


class UserDeletedReuse(ReuseRelatedActivity, Activity):
    key = "reuse:deleted"
    icon = "fa fa-remove"
    badge_type = "error"
    label = _("deleted a reuse")


@Reuse.on_create.connect
def on_user_created_reuse(reuse, **kwargs):
    UserCreatedReuse.emit(reuse, reuse.organization)


@Reuse.on_update.connect
def on_user_updated_reuse(reuse, **kwargs):
    UserUpdatedReuse.emit(reuse, reuse.organization, kwargs.get("changed_fields", []))


@Reuse.on_delete.connect
def on_user_deleted_reuse(reuse, **kwargs):
    UserDeletedReuse.emit(reuse, reuse.organization)
