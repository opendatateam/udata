from udata.auth import Permission, UserNeed

from udata.models import User, Organization

from udata.core.organization.permissions import OrganizationAdminNeed


class TransferPermission(Permission):
    '''Permissions to transfer an object assets'''
    def __init__(self, subject):
        if subject.organization:
            need = OrganizationAdminNeed(subject.organization.id)
        elif subject.owner:
            need = UserNeed(subject.owner.fs_uniquifier)
        super(TransferPermission, self).__init__(need)


class TransferResponsePermission(Permission):
    '''Permissions to transfer an object assets'''
    def __init__(self, transfer):
        if isinstance(transfer.recipient, Organization):
            need = OrganizationAdminNeed(transfer.recipient.id)
        elif isinstance(transfer.recipient, User):
            need = UserNeed(transfer.recipient.fs_uniquifier)
        super(TransferResponsePermission, self).__init__(need)
