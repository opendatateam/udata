# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from collections import namedtuple

from udata.auth import current_user, Permission

from udata.core.organization.permissions import OrganizationAdminNeed, OrganizationEditorNeed

ReuseOwnerNeed = namedtuple('reuse_owner', 'value')


def set_reuse_identity(identity, reuse):
    if not current_user.is_authenticated():
        return
    if reuse.owner and current_user.id == reuse.owner.id:
        identity.provides.add(ReuseOwnerNeed(str(reuse.id)))


class ReuseEditPermission(Permission):
    def __init__(self, reuse):
        needs = [ReuseOwnerNeed(str(reuse.id))]

        if reuse.organization:
            needs.append(OrganizationAdminNeed(reuse.organization.id))
            needs.append(OrganizationEditorNeed(reuse.organization.id))

        super(ReuseEditPermission, self).__init__(*needs)
