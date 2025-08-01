from udata.auth import Permission, UserNeed
from udata.core.organization.permissions import (
    OrganizationAdminNeed,
    OrganizationEditorNeed,
)
from udata.core.standard.models import Standard


class StandardEditPermission(Permission):
    def __init__(self, standard: Standard) -> None:
        needs = []

        if standard.organization:
            needs.append(OrganizationAdminNeed(standard.organization.id))
            needs.append(OrganizationEditorNeed(standard.organization.id))
        elif standard.owner:
            needs.append(UserNeed(standard.owner.fs_uniquifier))

        super(StandardEditPermission, self).__init__(*needs)
