from udata.auth import Permission, UserNeed
from udata.core.dataset.permissions import OwnablePermission
from udata.core.organization.permissions import (
    OrganizationAdminNeed,
    OrganizationEditorNeed,
)

from .models import Discussion, Message


# This is a hack to because double inheritance doesn't work really well with permissions.
# I simulate a class constructor with a function to keep the same API than other permissions
# but use the `.union()` of two permission under the hood.
def DiscussionAuthorOrSubjectOwnerPermission(discussion: Discussion):
    return OwnablePermission(discussion.subject).union(DiscussionAuthorPermission(discussion))


class DiscussionAuthorPermission(Permission):
    def __init__(self, discussion: Discussion):
        needs = []

        if discussion.organization:
            needs.append(OrganizationAdminNeed(discussion.organization.id))
            needs.append(OrganizationEditorNeed(discussion.organization.id))
        else:
            needs.append(UserNeed(discussion.user.fs_uniquifier))

        super(DiscussionAuthorPermission, self).__init__(*needs)


class DiscussionMessagePermission(Permission):
    def __init__(self, message: Message):
        needs = []

        if message.posted_by_organization:
            needs.append(OrganizationAdminNeed(message.posted_by_organization.id))
            needs.append(OrganizationEditorNeed(message.posted_by_organization.id))
        else:
            needs.append(UserNeed(message.posted_by.fs_uniquifier))

        super(DiscussionMessagePermission, self).__init__(*needs)
