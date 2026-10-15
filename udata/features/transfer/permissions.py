from udata.auth import Permission, UserNeed
from udata.core.organization.permissions import OrganizationAdminNeed
from udata.models import Organization


class TransferPermission(Permission):
    """Permissions to transfer an object assets"""

    def __init__(self, subject):
        # No need at all when nobody owns the subject: purging an organization only deletes
        # the organization, and `Owned.organization` nullifies itself, leaving its datasets
        # behind with neither an owner nor an organization. Such a subject has nobody
        # entitled to give it away, which is what an empty permission means (sysadmins
        # excepted, as everywhere else).
        needs = []
        if subject.organization:
            needs.append(OrganizationAdminNeed(subject.organization.id))
        elif subject.owner:
            needs.append(UserNeed(subject.owner.fs_uniquifier))
        super().__init__(*needs)


class TransferResponsePermission(Permission):
    """Permissions to transfer an object assets"""

    def __init__(self, transfer):
        if isinstance(transfer.recipient, Organization):
            need = OrganizationAdminNeed(transfer.recipient.id)
        else:
            need = UserNeed(transfer.recipient.fs_uniquifier)
        super().__init__(need)
