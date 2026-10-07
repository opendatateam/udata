import logging

from mongoengine import EmbeddedDocument
from mongoengine.fields import ReferenceField, StringField

from udata.api_fields import field, generate_fields
from udata.core.user.models import Role, User
from udata.features.notifications.actions import notifier
from udata.features.notifications.constants import NotificationType
from udata.features.notifications.events import NotificationEvent

from .models import (
    VALIDATION_ACCEPTED,
    VALIDATION_PENDING,
    VALIDATION_REFUSED,
    VALIDATION_STATES,
    HarvestSource,
)
from .signals import (
    harvest_source_created,
    harvest_source_deleted,
    harvest_source_refused,
    harvest_source_validated,
)

log = logging.getLogger(__name__)

# Superseded by `Notification.type`, kept until the front reads the type instead.
STATES_BY_TYPE = {
    NotificationType.HARVEST_SOURCE_PENDING: VALIDATION_PENDING,
    NotificationType.HARVEST_SOURCE_ACCEPTED: VALIDATION_ACCEPTED,
    NotificationType.HARVEST_SOURCE_REFUSED: VALIDATION_REFUSED,
}


@generate_fields()
class ValidateHarvesterNotificationDetails(EmbeddedDocument):
    source = field(
        ReferenceField(HarvestSource),
        readonly=True,
        nested_fields=HarvestSource.__read_fields__,
        auditable=False,
        allow_null=True,
        filterable={},
    )
    # Superseded by `Notification.type`, kept until the front reads the type instead.
    status = field(
        StringField(choices=list(VALIDATION_STATES), default=VALIDATION_PENDING),
        readonly=True,
        auditable=False,
        filterable={},
    )


class HarvestSourceEvent(NotificationEvent):
    def __init__(self, source: HarvestSource):
        self.source = source

    def via_app(self, recipient):
        return ValidateHarvesterNotificationDetails(
            source=self.source, status=STATES_BY_TYPE[self.type]
        )


class HarvestSourcePending(HarvestSourceEvent):
    """Only sysadmins can validate a source, so only they are asked to."""

    type = NotificationType.HARVEST_SOURCE_PENDING

    def recipients(self):
        admin_role = Role.objects(name="admin").first()
        if admin_role is None:
            return []
        return list(User.objects(roles=admin_role, active=True))


class HarvestSourceReviewed(HarvestSourceEvent):
    """The outcome goes back to whoever declared the source."""

    def recipients(self):
        if self.source.organization:
            return [member.user for member in self.source.organization.by_role("admin")]
        if self.source.owner:
            return [self.source.owner]
        return []


class HarvestSourceValidated(HarvestSourceReviewed):
    type = NotificationType.HARVEST_SOURCE_ACCEPTED


class HarvestSourceRefused(HarvestSourceReviewed):
    type = NotificationType.HARVEST_SOURCE_REFUSED


def _handle_pending_notifications(source: HarvestSource):
    """Reviewing the source answers the request sysadmins were sitting on."""
    from udata.features.notifications.models import Notification

    Notification.objects(
        details__source=source, type=NotificationType.HARVEST_SOURCE_PENDING, handled_at=None
    ).mark_handled()


@harvest_source_created.connect
def on_harvest_source_created(source: HarvestSource, **kwargs):
    HarvestSourcePending(source).dispatch()


@harvest_source_validated.connect
def on_harvest_source_validated(source: HarvestSource, **kwargs):
    _handle_pending_notifications(source)
    HarvestSourceValidated(source).dispatch()


@harvest_source_refused.connect
def on_harvest_source_refused(source: HarvestSource, **kwargs):
    _handle_pending_notifications(source)
    HarvestSourceRefused(source).dispatch()


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


@harvest_source_deleted.connect
def on_harvest_source_deleted(source, **kwargs):
    """Clean up notifications when a harvest source is deleted"""
    from udata.features.notifications.models import Notification

    try:
        Notification.objects(details__source=source).delete()
    except Exception as e:
        log.error(f"Error cleaning up notifications for deleted harvest source {source.id}: {e}")
