from udata.auth import Permission, UserNeed
from udata.core.organization.permissions import (
    OrganizationAdminNeed,
    OrganizationEditorNeed,
)

from .models import Message


class CloseDiscussionPermission(Permission):
    def __init__(self, discussion):
        needs = []
        subject = discussion.subject

        if getattr(subject, "organization", None):
            needs.append(OrganizationAdminNeed(subject.organization.id))
            needs.append(OrganizationEditorNeed(subject.organization.id))
        elif subject.owner:
            needs.append(UserNeed(subject.owner.fs_uniquifier))

        super(CloseDiscussionPermission, self).__init__(*needs)


class DiscussionMessagePermission(Permission):
    def __init__(self, message: Message):
        needs = []

        needs.append(UserNeed(message.posted_by.fs_uniquifier))

        super(DiscussionMessagePermission, self).__init__(*needs)
