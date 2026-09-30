from udata.auth import Permission, UserNeed
from udata.core.dataset.permissions import OwnablePermission
from udata.core.organization.permissions import (
    AssignmentNeed,
    OrganizationAdminNeed,
    OrganizationEditorNeed,
)
from udata.core.owned import Owned

from .models import Discussion, Message


def organization_voice_needs(organization, subject) -> list:
    """Needs to speak in the name of `organization` in a discussion about `subject`.

    Admins and editors speak for their organization everywhere, a reuser organization
    writing to a producer being the common case. A partial editor only edits the objects
    assigned to them, so they only speak for the organization on those.
    """
    needs = [OrganizationAdminNeed(organization.id), OrganizationEditorNeed(organization.id)]
    if isinstance(subject, Owned) and subject.organization == organization:
        needs.append(AssignmentNeed(subject.__class__.__name__, subject.id))
    return needs


# This is a hack to because double inheritance doesn't work really well with permissions.
# I simulate a class constructor with a function to keep the same API than other permissions
# but use the `.union()` of two permission under the hood.
def DiscussionAuthorOrSubjectOwnerPermission(discussion: Discussion):
    author_permission = DiscussionAuthorPermission(discussion)

    # A `Post` is a valid discussion subject but is not `Owned`: it has no `organization`,
    # and only sysadmins may edit it — which `Permission` already grants on every permission.
    if not isinstance(discussion.subject, Owned):
        return author_permission

    return OwnablePermission(discussion.subject).union(author_permission)


class DiscussionAuthorPermission(Permission):
    def __init__(self, discussion: Discussion):
        if discussion.organization:
            needs = organization_voice_needs(discussion.organization, discussion.subject)
        else:
            needs = [UserNeed(discussion.user.fs_uniquifier)]

        super(DiscussionAuthorPermission, self).__init__(*needs)


class DiscussionMessagePermission(Permission):
    def __init__(self, message: Message):
        if message.posted_by_organization:
            # `_instance` is the discussion holding this embedded message.
            needs = organization_voice_needs(
                message.posted_by_organization, message._instance.subject
            )
        else:
            needs = [UserNeed(message.posted_by.fs_uniquifier)]

        super(DiscussionMessagePermission, self).__init__(*needs)
