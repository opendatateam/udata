from collections import namedtuple
from functools import partial

from udata.auth import Permission, current_user, identity_loaded
from udata.core.organization.models import Organization
from udata.utils import get_by

OrganizationNeed = namedtuple("organization", ("role", "value"))
OrganizationAdminNeed = partial(OrganizationNeed, "admin")
OrganizationEditorNeed = partial(OrganizationNeed, "editor")
OrganizationPartialEditorNeed = partial(OrganizationNeed, "partial_editor")

AssignmentNeed = namedtuple("assignment", ("object_class", "object_id"))


class EditOrganizationPermission(Permission):
    """Permissions to edit organization assets"""

    def __init__(self, org):
        need = OrganizationAdminNeed(org.id)
        super(EditOrganizationPermission, self).__init__(need)


class OrganizationPrivatePermission(Permission):
    """Permission to see organization private assets"""

    def __init__(self, org):
        super(OrganizationPrivatePermission, self).__init__(
            OrganizationAdminNeed(org.id),
            OrganizationEditorNeed(org.id),
            OrganizationPartialEditorNeed(org.id),
        )


def organization_needs(user) -> set:
    """What `user` may do as a member of organizations: a role in each, and the objects
    assigned to them as a partial editor."""
    from udata.core.organization.assignment import Assignment

    needs = set()
    for org in Organization.objects(members__user=user.id).only("members"):
        membership = get_by(org.members, user=user)
        needs.add(OrganizationNeed(membership.role, org.id))
    for raw in Assignment.objects(user=user.id).only("subject").no_dereference().as_pymongo():
        subject = raw["subject"]
        needs.add(AssignmentNeed(subject["_cls"], subject["_ref"].id))
    return needs


@identity_loaded.connect
def inject_organization_needs(sender, identity, **kwargs):
    if current_user.is_authenticated:
        identity.provides.update(organization_needs(current_user._get_current_object()))
