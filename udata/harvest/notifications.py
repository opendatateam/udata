import logging

from udata.features.notifications.actions import notifier

from .models import VALIDATION_PENDING, HarvestSource

log = logging.getLogger(__name__)


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
