from udata.auth import Permission, UserNeed
from udata.core.organization.permissions import OrganizationAdminNeed
from udata.models import Organization, User


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
        # Same as above: `Transfer.recipient` is a choice-less generic reference, so
        # transfers pointing at something that is neither a user nor an organization can
        # already sit in the database. Nobody can respond to those.
        needs = []
        if isinstance(transfer.recipient, Organization):
            needs.append(OrganizationAdminNeed(transfer.recipient.id))
        elif isinstance(transfer.recipient, User):
            needs.append(UserNeed(transfer.recipient.fs_uniquifier))
        super().__init__(*needs)
