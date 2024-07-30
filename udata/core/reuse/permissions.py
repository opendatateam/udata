from udata.auth import Permission, UserNeed
from udata.core.organization.permissions import (
    OrganizationAdminNeed,
    OrganizationEditorNeed,
)
from udata.core.reuse.models import Reuse


class ReuseEditPermission(Permission):
    def __init__(self, reuse: Reuse) -> None:
        needs = []

        if reuse.organization:
            needs.append(OrganizationAdminNeed(reuse.organization.id))
            needs.append(OrganizationEditorNeed(reuse.organization.id))
        elif reuse.owner:
            needs.append(UserNeed(reuse.owner.fs_uniquifier))

        super(ReuseEditPermission, self).__init__(*needs)
