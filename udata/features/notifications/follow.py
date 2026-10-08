from flask import has_request_context, request
from mongoengine import NotUniqueError

from udata.api import HEADER_API_KEY
from udata.auth import current_user
from udata.core.dataservices.models import Dataservice
from udata.core.dataset.models import Dataset
from udata.core.discussions.signals import on_new_discussion, on_new_discussion_comment
from udata.core.reuse.models import Reuse
from udata.core.user.models import User
from udata.features.notifications.constants import FollowOrigin
from udata.features.notifications.settings import NotificationSetting


def follow_worked_on(user: User, subject, origin: FollowOrigin) -> None:
    """Make a member who worked on a subject of their organization follow it.

    Having edited a dataset, or answered about it, is a lasting reason to hear about it,
    whatever one's role is now or later: an administrator who becomes an editor keeps
    what they took care of. A decision already taken about the subject is left as is, so
    that working on something one chose to ignore does not bring it back.

    Nothing is announced: the way out comes with the first notification it brings, when
    it is something to decide about.

    Sysadmins are left out: they edit and answer on behalf of the platform, not of the
    organizations they happen to belong to.
    """
    organization = getattr(subject, "organization", None)
    if organization is None or not organization.is_member(user) or user.sysadmin:
        return
    if NotificationSetting.objects(user=user, scope=subject).first():
        return
    try:
        NotificationSetting.objects.create(user=user, scope=subject, enabled=True, origin=origin)
    except NotUniqueError:
        # A concurrent edit by the same member created it in between: the edit itself
        # is already saved and must not fail over it.
        pass


def follow_if_by_hand(subject, origin: FollowOrigin, user: User | None = None) -> None:
    """Only a person working through data.gouv.fr: a script publishing with an API key has
    not worked on each of the subjects it touches, and harvesting has no user. Anything
    calling with an OAuth token is taken for a script too, a person editing through
    another site included: the token does not tell them apart. Whoever worked is the
    current user, unless the change says who did it."""
    if (
        not has_request_context()
        or request.headers.get(HEADER_API_KEY)
        or request.headers.get("Authorization", "").lower().startswith("bearer ")
    ):
        return
    if user is None:
        if not current_user or not current_user.is_authenticated:
            return
        user = current_user._get_current_object()
    follow_worked_on(user, subject, origin)


@Dataset.on_create.connect
@Dataset.on_update.connect
@Reuse.on_create.connect
@Reuse.on_update.connect
@Dataservice.on_create.connect
@Dataservice.on_update.connect
def on_subject_saved(subject, **kwargs):
    follow_if_by_hand(subject, FollowOrigin.EDITED)


@Dataset.on_resource_added.connect
@Dataset.on_resource_updated.connect
@Dataset.on_resource_removed.connect
def on_resource_changed(sender, document, **kwargs):
    follow_if_by_hand(document, FollowOrigin.EDITED)


# Answering about a dataset is following it: the next questions on it will be for the
# same people. A new discussion is its first message.
@on_new_discussion.connect
@on_new_discussion_comment.connect
def on_discussed(discussion, message: int = 0, **kwargs):
    author = discussion.discussion[message].posted_by
    follow_if_by_hand(discussion.subject, FollowOrigin.DISCUSSED, author)
