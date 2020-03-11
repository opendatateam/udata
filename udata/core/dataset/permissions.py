from udata.auth import Permission, UserNeed

from udata.core.organization.permissions import (
    OrganizationAdminNeed, OrganizationEditorNeed
)

from .models import Resource


class OwnablePermission(Permission):
    '''A generic permission for ownable objects (with owner or organization)'''
    def __init__(self, obj):
        needs = []

        if obj.organization:
            needs.append(OrganizationAdminNeed(obj.organization.id))
            needs.append(OrganizationEditorNeed(obj.organization.id))
        elif obj.owner:
            needs.append(UserNeed(obj.owner.id))

        super(OwnablePermission, self).__init__(*needs)


class DatasetEditPermission(OwnablePermission):
    '''Permissions to edit a Dataset'''
    pass


class ResourceEditPermission(OwnablePermission):
    '''Permissions to edit a Resource (aka. its dataset) or community resource'''
    def __init__(self, obj):
        if isinstance(obj, Resource):
            raise ValueError('Resource permissions are holded by its dataset')
        super(ResourceEditPermission, self).__init__(obj)
