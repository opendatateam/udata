import logging

from mongoengine import EmbeddedDocument
from mongoengine.fields import ReferenceField, StringField

from udata.api_fields import field, generate_fields
from udata.core.user.models import Role, User
from udata.features.notifications.constants import NotificationReason, NotificationType
from udata.features.notifications.events import NotificationEvent, Recipient
from udata.i18n import lazy_gettext as _

from .models import HarvestSource
from .signals import (
    harvest_source_created,
    harvest_source_deleted,
    harvest_source_refused,
    harvest_source_validated,
)

log = logging.getLogger(__name__)


@generate_fields()
class ValidateHarvesterNotificationDetails(EmbeddedDocument):
    # Superseded by `Notification.type` and read by nothing, but still written by the
    # previous release while it is being replaced: an undeclared field would make such a
    # notification fail to load. Dropped, with its values, by the next release.
    status = StringField()

    source = field(
        ReferenceField(HarvestSource),
        readonly=True,
        nested_fields=HarvestSource.__read_fields__,
        auditable=False,
        allow_null=True,
        filterable={},
    )


class HarvestSourceEvent(NotificationEvent):
    def __init__(self, source: HarvestSource):
        self.source = source

    @property
    def subject(self):
        return self.source

    def scopes(self):
        # A source is not something a rule names: its organization is.
        return [self.source.organization] if self.source.organization else []

    def via_app(self, recipient):
        return ValidateHarvesterNotificationDetails(source=self.source)


class HarvestSourcePending(HarvestSourceEvent):
    """Only sysadmins can validate a source, so only they are asked to."""

    type = NotificationType.HARVEST_SOURCE_PENDING

    def recipients(self):
        admin_role = Role.objects(name="admin").first()
        if admin_role is None:
            return []
        return [
            Recipient(user, frozenset({NotificationReason.SYSADMIN}))
            for user in User.objects(roles=admin_role, active=True)
        ]


class HarvestSourceReviewed(HarvestSourceEvent):
    """The outcome goes back to whoever declared the source."""

    reaches_subscribers = False

    def recipients(self):
        if self.source.organization:
            return [
                Recipient.from_member(member)
                for member in self.source.organization.by_role("admin")
            ]
        if self.source.owner:
            return [Recipient(self.source.owner, frozenset({NotificationReason.OWNER}))]
        return []


class HarvestSourceValidated(HarvestSourceReviewed):
    type = NotificationType.HARVEST_SOURCE_ACCEPTED
    label = _("Validated harvesters")


class HarvestSourceRefused(HarvestSourceReviewed):
    type = NotificationType.HARVEST_SOURCE_REFUSED
    label = _("Refused harvesters")


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


@harvest_source_deleted.connect
def on_harvest_source_deleted(source, **kwargs):
    """Clean up notifications when a harvest source is deleted"""
    from udata.features.notifications.models import Notification

    try:
        Notification.objects(details__source=source).delete()
    except Exception as e:
        log.error(f"Error cleaning up notifications for deleted harvest source {source.id}: {e}")
