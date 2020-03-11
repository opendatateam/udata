from udata.auth import Permission, UserNeed

from udata.core.organization.permissions import (
    OrganizationAdminNeed, OrganizationEditorNeed
)


class CloseIssuePermission(Permission):
    def __init__(self, issue):
        needs = []
        subject = issue.subject

        if getattr(subject, 'organization'):
            needs.append(OrganizationAdminNeed(subject.organization.id))
            needs.append(OrganizationEditorNeed(subject.organization.id))
        elif subject.owner:
            needs.append(UserNeed(subject.owner.id))

        super(CloseIssuePermission, self).__init__(*needs)
