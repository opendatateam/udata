import logging

from udata.api_fields import field, generate_fields
from udata.core.organization.api_fields import org_ref_fields
from udata.core.organization.models import MembershipRequest, Organization
from udata.core.user.api_fields import user_ref_fields
from udata.core.user.models import User
from udata.features.notifications.actions import notifier
from udata.models import db

log = logging.getLogger(__name__)


@generate_fields()
class MembershipRequestNotificationDetails(db.EmbeddedDocument):
    request_organization = field(
        db.ReferenceField(Organization),
        readonly=True,
        nested_fields=org_ref_fields,
        auditable=False,
        allow_null=True,
        filterable={},
    )
    request_user = field(
        db.ReferenceField(User),
        nested_fields=user_ref_fields,
        readonly=True,
        auditable=False,
        allow_null=True,
        filterable={},
    )


@MembershipRequest.after_create.connect
def on_new_membership_request(request: MembershipRequest, **kwargs):
    from udata.features.notifications.models import Notification

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
            existing = Notification.objects(
                user=admin_user,
                details__request_organization=organization,
                details__request_user=request.user,
            ).first()

            if not existing:
                notification = Notification(
                    user=admin_user,
                    details=MembershipRequestNotificationDetails(
                        request_organization=organization, request_user=request.user
                    ),
                )
                notification.created_at = request.created
                notification.save()
        except Exception as e:
            log.error(
                f"Error creating notification for user {admin_user.id} "
                f"and organization {organization.id}: {e}"
            )


@MembershipRequest.after_handle.connect
def on_handle_membership_request(request: MembershipRequest, **kwargs):
    from udata.features.notifications.models import Notification

    organization = kwargs.get("org")

    if organization is None:
        return

    notifications = Notification.objects(
        details__request_organization=organization,
        details__request_user=request.user,
    )

    for notification in notifications:
        notification.handled_at = request.handled_on
        notification.save()


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
