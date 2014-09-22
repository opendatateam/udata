# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from collections import namedtuple

from flask import g

from udata.auth import current_user, Permission

from udata.core.organization.permissions import OrganizationAdminNeed, OrganizationEditorNeed

DatasetOwnerNeed = namedtuple('dataset_owner', 'value')
ResourceOwnerNeed = namedtuple('resource_owner', 'value')


def set_dataset_identity(identity, dataset):
    if not current_user.is_authenticated():
        return
    if dataset.owner and current_user.id == dataset.owner.id:
        identity.provides.add(DatasetOwnerNeed(str(dataset.id)))

    for resource in dataset.resources + dataset.community_resources:
        if resource.owner and current_user.id == resource.owner.id:
            identity.provides.add(ResourceOwnerNeed(str(resource.id)))


class DatasetEditPermission(Permission):
    def __init__(self, dataset):
        needs = [DatasetOwnerNeed(str(dataset.id))]

        if dataset.organization:
            needs.append(OrganizationAdminNeed(dataset.organization.id))
            needs.append(OrganizationEditorNeed(dataset.organization.id))

        super(DatasetEditPermission, self).__init__(*needs)


class CommunityResourceEditPermission(Permission):
    def __init__(self, resource):
        needs = [ResourceOwnerNeed(str(resource.id))]

        super(CommunityResourceEditPermission, self).__init__(*needs)
