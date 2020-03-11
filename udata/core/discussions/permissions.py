from udata.auth import Permission, UserNeed

from udata.core.organization.permissions import (
    OrganizationAdminNeed, OrganizationEditorNeed
)


class CloseDiscussionPermission(Permission):
    def __init__(self, discussion):
        needs = []
        subject = discussion.subject

        if getattr(subject, 'organization'):
            needs.append(OrganizationAdminNeed(subject.organization.id))
            needs.append(OrganizationEditorNeed(subject.organization.id))
        elif subject.owner:
            needs.append(UserNeed(subject.owner.id))

        super(CloseDiscussionPermission, self).__init__(*needs)
