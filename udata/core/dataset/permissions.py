# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.auth import Permission, UserNeed

from udata.core.organization.permissions import (
    OrganizationAdminNeed, OrganizationEditorNeed
)

from .models import CommunityResource


class DatasetEditPermission(Permission):
    def __init__(self, dataset):
        needs = []

        if dataset.organization:
            needs.append(OrganizationAdminNeed(dataset.organization.id))
            needs.append(OrganizationEditorNeed(dataset.organization.id))
        elif dataset.owner:
            needs.append(UserNeed(dataset.owner.id))

        super(DatasetEditPermission, self).__init__(*needs)


class ResourceEditPermission(Permission):
    def __init__(self, resource, dataset):
        needs = []
        obj = resource if isinstance(resource, CommunityResource) else dataset

        if obj.organization:
            needs.append(OrganizationAdminNeed(obj.organization.id))
            needs.append(OrganizationEditorNeed(obj.organization.id))
        elif obj.owner:
            needs.append(UserNeed(obj.owner.id))

        super(ResourceEditPermission, self).__init__(*needs)
