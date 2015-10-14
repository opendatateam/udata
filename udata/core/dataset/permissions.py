# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.auth import Permission, UserNeed

from udata.core.organization.permissions import (
    OrganizationAdminNeed, OrganizationEditorNeed
)


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
        if hasattr(resource, 'organization') or hasattr(resource, 'owner'):
            # This is a community resource.
            if resource.organization:
                needs.append(OrganizationAdminNeed(resource.organization.id))
                needs.append(OrganizationEditorNeed(resource.organization.id))
            elif resource.owner:
                needs.append(UserNeed(resource.owner.id))
        else:
            if dataset.organization:
                needs.append(OrganizationAdminNeed(dataset.organization.id))
                needs.append(OrganizationEditorNeed(dataset.organization.id))
            elif dataset.owner:
                needs.append(UserNeed(dataset.owner.id))

        super(ResourceEditPermission, self).__init__(*needs)
