# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.auth import Permission, UserNeed

from udata.core.organization.permissions import (
    OrganizationAdminNeed, OrganizationEditorNeed
)


class ReuseEditPermission(Permission):
    def __init__(self, reuse):
        needs = []

        if reuse.organization:
            needs.append(OrganizationAdminNeed(reuse.organization.id))
            needs.append(OrganizationEditorNeed(reuse.organization.id))
        elif reuse.owner:
            needs.append(UserNeed(reuse.owner.id))

        super(ReuseEditPermission, self).__init__(*needs)
