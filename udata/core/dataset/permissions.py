from udata.core.owned import OwnablePermission

from .models import Resource


class DatasetEditPermission(OwnablePermission):
    '''Permissions to edit a Dataset'''
    pass


class ResourceEditPermission(OwnablePermission):
    '''Permissions to edit a Resource (aka. its dataset) or community resource'''
    def __init__(self, obj):
        if isinstance(obj, Resource):
            raise ValueError('Resource permissions are holded by its dataset')
        super(ResourceEditPermission, self).__init__(obj)
