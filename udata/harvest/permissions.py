from udata.auth import Permission, UserNeed
from udata.core.dataset.permissions import OwnablePermission
from udata.core.organization.permissions import OrganizationAdminNeed


class HarvestSourcePermission(OwnablePermission):
    """Permission for basic harvest source operations (preview)
    Allows organization admins, editors, or owner.
    """

    pass


class HarvestSourceAdminPermission(Permission):
    """Permission for sensitive harvest source operations (edit, delete, run)
    Allows only organization admins or owner (not editors).
    """

    def __init__(self, source) -> None:
        needs = []

        if source.organization:
            needs.append(OrganizationAdminNeed(source.organization.id))
        elif source.owner:
            needs.append(UserNeed(source.owner.fs_uniquifier))

        super(HarvestSourceAdminPermission, self).__init__(*needs)
