from udata.auth import Permission
from udata.core.organization.permissions import OrganizationAdminNeed


class BadgePermission(Permission):
    def __init__(self, badge):
        needs = []
        subject = badge.subject
        if getattr(subject, "organization", False):  # This is a Dataset.
            organization_id = subject.organization.id
        else:  # This is an Organization.
            organization_id = subject.id
        needs.append(OrganizationAdminNeed(organization_id))

        super(BadgePermission, self).__init__(*needs)
