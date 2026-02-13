import logging
from datetime import datetime

from udata.api_fields import field, generate_fields
from udata.core.user.models import Role, User
from udata.features.notifications.actions import notifier
from udata.mongo import db

from .api import source_fields
from .models import (
    VALIDATION_ACCEPTED,
    VALIDATION_PENDING,
    VALIDATION_REFUSED,
    VALIDATION_STATES,
    HarvestSource,
)
from .signals import harvest_source_created, harvest_source_refused, harvest_source_validated

log = logging.getLogger(__name__)


@generate_fields()
class ValidateHarvesterNotificationDetails(db.EmbeddedDocument):
    source = field(
        db.ReferenceField(HarvestSource),
        readonly=True,
        nested_fields=source_fields,
        auditable=False,
        allow_null=True,
        filterable={},
    )
    status = field(
        db.StringField(choices=list(VALIDATION_STATES), default=VALIDATION_PENDING),
        readonly=True,
        auditable=False,
        filterable={},
    )


@harvest_source_created.connect
def on_harvest_source_created(source: HarvestSource, **kwargs):
    from udata.features.notifications.models import Notification

    """Create notification for sysadmins when a new harvest source is created"""
    admin_role = Role.objects(name="admin").first()
    if admin_role is None:
        return

    sysadmins = User.objects(roles=admin_role, active=True)

    for admin in sysadmins:
        try:
            existing = Notification.objects(
                user=admin,
                details__source=source,
            ).first()

            if not existing:
                notification = Notification(
                    user=admin,
                    details=ValidateHarvesterNotificationDetails(
                        source=source,
                    ),
                )
                notification.save()
        except Exception as e:
            log.error(
                f"Error creating notification for user {admin.id} "
                f"and harvest source {source.id}: {e}"
            )


def _get_source_recipients(source: HarvestSource):
    """Get the recipients for a harvest source notification (owner or org admins)"""
    if source.organization:
        return [member.user for member in source.organization.members if member.role == "admin"]
    elif source.owner:
        return [source.owner]
    return []


@harvest_source_validated.connect
def on_harvest_source_validated(source: HarvestSource, **kwargs):
    from udata.features.notifications.models import Notification

    """Create notification for source owner/org admins when a harvest source is validated"""
    recipients = _get_source_recipients(source)

    # Update existing VALIDATION_PENDING notifications to mark them as handled
    pending_notifications = Notification.objects(
        details__source=source, details__status=VALIDATION_PENDING, handled_at=None
    )
    for notification in pending_notifications:
        notification.handled_at = datetime.utcnow()
        notification.save()

    for recipient in recipients:
        try:
            notification = Notification(
                user=recipient,
                details=ValidateHarvesterNotificationDetails(
                    source=source,
                    status=VALIDATION_ACCEPTED,
                ),
            )
            notification.save()
        except Exception as e:
            log.error(
                f"Error creating validated notification for user {recipient.id} "
                f"and harvest source {source.id}: {e}"
            )


@harvest_source_refused.connect
def on_harvest_source_refused(source: HarvestSource, **kwargs):
    from udata.features.notifications.models import Notification

    """Create notification for source owner/org admins when a harvest source is refused"""
    recipients = _get_source_recipients(source)

    # Update existing VALIDATION_PENDING notifications to mark them as handled
    pending_notifications = Notification.objects(
        details__source=source, details__status=VALIDATION_PENDING, handled_at=None
    )
    for notification in pending_notifications:
        notification.handled_at = datetime.utcnow()
        notification.save()

    for recipient in recipients:
        try:
            notification = Notification(
                user=recipient,
                details=ValidateHarvesterNotificationDetails(
                    source=source,
                    status=VALIDATION_REFUSED,
                ),
            )
            notification.save()
        except Exception as e:
            log.error(
                f"Error creating refused notification for user {recipient.id} "
                f"and harvest source {source.id}: {e}"
            )


@notifier("validate_harvester")
def validate_harvester_notifications(user):
    """Notify admins about pending harvester validation"""
    if not user.sysadmin:
        return []

    notifications = []

    # Only fetch required fields for notification serialization
    # Greatly improve performances and memory usage
    qs = HarvestSource.objects(validation__state=VALIDATION_PENDING)
    qs = qs.only("id", "created_at", "name")

    for source in qs:
        notifications.append(
            (
                source.created_at,
                {
                    "id": source.id,
                    "name": source.name,
                },
            )
        )

    return notifications
