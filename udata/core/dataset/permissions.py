# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask.ext.principal import UserNeed

from udata.auth import Permission

from udata.core.organization.permissions import OrganizationAdminNeed, OrganizationEditorNeed


class DatasetEditPermission(Permission):
    def __init__(self, dataset):
        needs = []

        if dataset.organization:
            needs.append(OrganizationAdminNeed(dataset.organization.id))
            needs.append(OrganizationEditorNeed(dataset.organization.id))
        elif dataset.owner:
            needs.append(UserNeed(dataset.owner.id))

        super(DatasetEditPermission, self).__init__(*needs)


class CommunityResourceEditPermission(Permission):
    def __init__(self, resource):
        needs = []
        if resource.owner:
            needs.append(UserNeed(resource.owner.id))

        super(CommunityResourceEditPermission, self).__init__(*needs)
