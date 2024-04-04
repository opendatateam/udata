from flask_security import current_user

from udata.i18n import lazy_gettext as _
from udata.models import db, Organization, Activity


__all__ = (
    'UserCreatedOrganization', 'UserUpdatedOrganization', 'OrgRelatedActivity'
)


class OrgRelatedActivity(object):
    related_to = db.ReferenceField('Organization')
    template = 'activity/organization.html'


class UserCreatedOrganization(OrgRelatedActivity, Activity):
    key = 'organization:created'
    icon = 'fa fa-plus'
    badge_type = 'success'
    label = _('created an organization')


class UserUpdatedOrganization(OrgRelatedActivity, Activity):
    key = 'organization:updated'
    icon = 'fa fa-pencil'
    badge_type = 'error'
    label = _('updated an organization')


@Organization.on_create.connect
def on_user_created_organization(organization):
    if current_user and current_user.is_authenticated:
        UserCreatedOrganization.emit(organization, organization)


@Organization.on_update.connect
def on_user_updated_organization(organization):
    if current_user and current_user.is_authenticated:
        UserUpdatedOrganization.emit(organization, organization)
