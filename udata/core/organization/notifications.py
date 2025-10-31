import logging

from mongoengine import NULLIFY

from udata.api_fields import field, generate_fields
from udata.core.organization.api_fields import org_ref_fields
from udata.core.organization.models import Member, MembershipRequest, Organization
from udata.core.user.api_fields import user_ref_fields
from udata.core.user.models import User

from udata.features.notifications.actions import notifier
from udata.features.notifications.models import Notification
from udata.models import db

log = logging.getLogger(__name__)


@generate_fields()
class MembershipRequestNotification(Notification):
    request_organization = field(
        db.ReferenceField(Organization, reverse_delete_rule=NULLIFY),
        readonly=True,
        nested_fields=org_ref_fields,
        auditable=False,
        allow_null=True,
        filterable={},
    )
    request_user = field(
        db.ReferenceField(User, reverse_delete_rule=NULLIFY),
        nested_fields=user_ref_fields,
        readonly=True,
        auditable=False,
        allow_null=True,
        filterable={},
    )

@MembershipRequest.after_save.connect
def on_new_membership_request(request: MembershipRequest,  **kwargs):
    """Create notification when a new membership request is created"""
    organization = kwargs.get("org")

    if organization is None:
        return
    
    # Get all admin users for the organization
    admin_users = [member.user for member in organization.members if member.role == "admin"]
    
    # For each pending request, check if a notification already exists
    for admin_user in admin_users:
        try:
            # Check if notification already exists
            existing = MembershipRequestNotification.objects(
                user=admin_user,
                request_organization=organization,
                request_user=request.user,
            ).first()
            
            if not existing:
                notification = MembershipRequestNotification(
                    user=admin_user,
                    request_organization=organization,
                    request_user=request.user,
                )
                notification.created_at = request.created
                notification.save()
        except Exception as e:
            log.error(
                f"Error creating notification for user {admin_user.id} "
                f"and organization {organization.id}: {e}"
            )

@notifier("membership_request")
def membership_request_notifications(user):
    """Notify user about pending membership requests"""
    orgs = [o for o in user.organizations if o.is_admin(user)]
    notifications = []

    for org in orgs:
        for request in org.pending_requests:
            notifications.append(
                (
                    request.created,
                    {
                        "id": request.id,
                        "organization": org.id,
                        "user": {
                            "id": request.user.id,
                            "fullname": request.user.fullname,
                            "avatar": str(request.user.avatar),
                        },
                    },
                )
            )

    return notifications
