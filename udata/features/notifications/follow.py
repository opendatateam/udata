from flask import has_request_context, request

from udata.api import HEADER_API_KEY
from udata.auth import current_user
from udata.core.dataservices.models import Dataservice
from udata.core.dataset.models import Dataset
from udata.core.reuse.models import Reuse
from udata.core.user.models import User
from udata.features.notifications.constants import FollowOrigin
from udata.features.notifications.settings import NotificationSetting


def follow_worked_on(user: User, subject) -> None:
    """Make a member who worked on a subject of their organization follow it.

    Having edited a dataset is a lasting reason to hear about it, whatever one's role
    is now or later: an administrator who becomes an editor keeps what they took care
    of. A decision already taken about the subject is left as is, so that editing
    something one chose to ignore does not bring it back.

    Nothing is announced: the way out comes with the first notification it brings, when
    it is something to decide about.
    """
    organization = getattr(subject, "organization", None)
    if organization is None or not organization.is_member(user):
        return
    if NotificationSetting.objects(user=user, scope=subject).first():
        return
    NotificationSetting.objects.create(
        user=user, scope=subject, enabled=True, origin=FollowOrigin.EDITED
    )


def follow_if_edited_by_hand(subject) -> None:
    """Only a person editing through the site: a script publishing with an API key has
    not worked on each of the subjects it touches, and harvesting has no user."""
    if not has_request_context() or request.headers.get(HEADER_API_KEY):
        return
    if not current_user or not current_user.is_authenticated:
        return
    follow_worked_on(current_user._get_current_object(), subject)


@Dataset.on_create.connect
@Dataset.on_update.connect
@Reuse.on_create.connect
@Reuse.on_update.connect
@Dataservice.on_create.connect
@Dataservice.on_update.connect
def on_subject_saved(subject, **kwargs):
    follow_if_edited_by_hand(subject)


@Dataset.on_resource_added.connect
@Dataset.on_resource_updated.connect
@Dataset.on_resource_removed.connect
def on_resource_changed(sender, document, **kwargs):
    follow_if_edited_by_hand(document)
