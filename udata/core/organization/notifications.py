import logging

from mongoengine import EmbeddedDocument
from mongoengine.fields import ReferenceField, StringField

from udata.api_fields import field, generate_fields
from udata.core.organization.api_fields import org_ref_fields
from udata.core.organization.models import MembershipRequest, Organization
from udata.core.user.api_fields import user_ref_fields
from udata.core.user.models import User
from udata.features.notifications.actions import notifier

log = logging.getLogger(__name__)


@generate_fields()
class MembershipRequestNotificationDetails(EmbeddedDocument):
    request_organization = field(
        ReferenceField(Organization),
        readonly=True,
        nested_fields=org_ref_fields,
        auditable=False,
        allow_null=True,
        filterable={},
    )
    request_user = field(
        ReferenceField(User),
        nested_fields=user_ref_fields,
        readonly=True,
        auditable=False,
        allow_null=True,
        filterable={},
    )
    kind = field(
        StringField(default="request"),
        readonly=True,
        auditable=False,
        filterable={},
    )


@generate_fields()
class NewBadgeNotificationDetails(EmbeddedDocument):
    organization = field(
        ReferenceField(Organization),
        readonly=True,
        nested_fields=org_ref_fields,
        auditable=False,
        allow_null=True,
        filterable={},
    )
    kind = field(
        StringField(),
        readonly=True,
        auditable=False,
        allow_null=True,
        filterable={},
    )


@generate_fields()
class MembershipAcceptedNotificationDetails(EmbeddedDocument):
    organization = field(
        ReferenceField(Organization),
        readonly=True,
        nested_fields=org_ref_fields,
        auditable=False,
        allow_null=True,
        filterable={},
    )


@generate_fields()
class MembershipRefusedNotificationDetails(EmbeddedDocument):
    organization = field(
        ReferenceField(Organization),
        readonly=True,
        nested_fields=org_ref_fields,
        auditable=False,
        allow_null=True,
        filterable={},
    )


@MembershipRequest.after_create.connect
def on_new_membership_request(request: MembershipRequest, **kwargs):
    from udata.features.notifications.models import Notification

    """Create notification when a new membership request or invitation is created"""
    organization = kwargs.get("org")

    if organization is None:
        return

    if request.kind == "invitation":
        # Invitation: notify the invited user
        if request.user is None:
            return
        recipients = [request.user]
    else:
        # Request: notify all org admins
        recipients = [member.user for member in organization.members if member.role == "admin"]

    for recipient in recipients:
        try:
            existing = Notification.objects(
                user=recipient,
                handled_at=None,
                details__request_organization=organization,
                details__request_user=request.user,
            ).first()

            if not existing:
                notification = Notification(
                    user=recipient,
                    details=MembershipRequestNotificationDetails(
                        request_organization=organization,
                        request_user=request.user,
                        kind=request.kind,
                    ),
                )
                notification.created_at = request.created
                notification.save()
        except Exception as e:
            log.error(
                f"Error creating notification for user {recipient.id} "
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
