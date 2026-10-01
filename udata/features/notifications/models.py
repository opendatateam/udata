from datetime import UTC, datetime

from flask_restx.inputs import boolean
from mongoengine import NULLIFY, Q, ValidationError
from mongoengine.fields import (
    DateTimeField,
    EnumField,
    GenericEmbeddedDocumentField,
    ReferenceField,
)

from udata.api_fields import field, generate_fields
from udata.core.dataservices.notifications import DataserviceCreatedNotificationDetails
from udata.core.discussions.notifications import DiscussionNotificationDetails
from udata.core.organization.notifications import (
    MembershipAcceptedNotificationDetails,
    MembershipRefusedNotificationDetails,
    MembershipRequestNotificationDetails,
    NewBadgeNotificationDetails,
)
from udata.core.reuse.notifications import ReuseCreatedNotificationDetails
from udata.core.user.models import User
from udata.features.notifications.constants import TYPES_REQUIRING_ACTION, NotificationType
from udata.features.transfer.notifications import TransferRequestNotificationDetails
from udata.harvest.notifications import ValidateHarvesterNotificationDetails
from udata.mongo.datetime_fields import Datetimed
from udata.mongo.document import UDataDocument as Document
from udata.mongo.queryset import UDataQuerySet
from udata.mongo.uuid_fields import AutoUUIDField

# The payload shape each type comes with. Several types legitimately map to the
# same class; what matters is that the relation is a function, so that knowing
# the type is enough to know which fields `details` exposes.
DETAILS_BY_TYPE: dict[NotificationType, type] = {
    NotificationType.DISCUSSION_NEW: DiscussionNotificationDetails,
    NotificationType.DISCUSSION_COMMENT: DiscussionNotificationDetails,
    NotificationType.DISCUSSION_CLOSED: DiscussionNotificationDetails,
    NotificationType.ORGANIZATION_MEMBERSHIP_REQUESTED: MembershipRequestNotificationDetails,
    NotificationType.ORGANIZATION_MEMBERSHIP_INVITED: MembershipRequestNotificationDetails,
    NotificationType.ORGANIZATION_MEMBERSHIP_ACCEPTED: MembershipAcceptedNotificationDetails,
    NotificationType.ORGANIZATION_MEMBERSHIP_REFUSED: MembershipRefusedNotificationDetails,
    NotificationType.ORGANIZATION_BADGE_CERTIFIED: NewBadgeNotificationDetails,
    NotificationType.ORGANIZATION_BADGE_PUBLIC_SERVICE: NewBadgeNotificationDetails,
    NotificationType.ORGANIZATION_BADGE_COMPANY: NewBadgeNotificationDetails,
    NotificationType.ORGANIZATION_BADGE_ASSOCIATION: NewBadgeNotificationDetails,
    NotificationType.ORGANIZATION_BADGE_LOCAL_AUTHORITY: NewBadgeNotificationDetails,
    NotificationType.REUSE_CREATED: ReuseCreatedNotificationDetails,
    NotificationType.DATASERVICE_CREATED: DataserviceCreatedNotificationDetails,
    NotificationType.TRANSFER_REQUESTED: TransferRequestNotificationDetails,
    NotificationType.HARVEST_SOURCE_PENDING: ValidateHarvesterNotificationDetails,
    NotificationType.HARVEST_SOURCE_ACCEPTED: ValidateHarvesterNotificationDetails,
    NotificationType.HARVEST_SOURCE_REFUSED: ValidateHarvesterNotificationDetails,
}


class NotificationQuerySet(UDataQuerySet):
    def with_organization_in_details(self, organization):
        """This function must be updated to handle new details cases"""
        return self.filter(
            Q(details__request_organization=organization) | Q(details__organization=organization)
        )

    def with_user_in_details(self, user):
        """This function must be updated to handle new details cases"""
        return self.filter(details__request_user=user)

    def mark_handled(self, at=None):
        """The subject got acted upon, so whatever was pending about it is resolved.

        A queryset update rather than a loop of saves: `last_modified` has to be set
        explicitly since it is otherwise filled by a `pre_save` handler.
        """
        now = datetime.now(UTC)
        return self.update(set__handled_at=at or now, set__last_modified=now)


def is_handled(base_query, filter_value):
    if filter_value is None:
        return base_query
    if filter_value is True:
        return base_query.filter(handled_at__ne=None)
    return base_query.filter(handled_at=None)


@generate_fields()
class Notification(Datetimed, Document[NotificationQuerySet]):
    meta = {
        "ordering": ["-created_at"],
        "queryset_class": NotificationQuerySet,
    }

    id = field(AutoUUIDField(primary_key=True))
    type = field(
        EnumField(NotificationType, required=True),
        readonly=True,
        auditable=False,
        filterable={},
    )
    handled_at = field(
        DateTimeField(),
        sortable=True,
        auditable=False,
        filterable={"key": "handled", "query": is_handled, "type": boolean},
    )
    user = field(
        ReferenceField(User, reverse_delete_rule=NULLIFY),
        readonly=True,
        allow_null=True,
        auditable=False,
        filterable={},
    )
    details = field(
        GenericEmbeddedDocumentField(choices=tuple(dict.fromkeys(DETAILS_BY_TYPE.values()))),
        generic=True,
    )

    @field(
        description="Whether the notification is resolved by acting on its subject "
        "rather than by reading it"
    )
    def requires_action(self, **kwargs) -> bool:
        return self.type in TYPES_REQUIRING_ACTION

    def clean(self):
        super().clean()
        if self.type is None:
            # Reported by the `required` validation, which mongoengine runs after clean()
            return
        expected = DETAILS_BY_TYPE[self.type]
        if not isinstance(self.details, expected):
            raise ValidationError(
                f"A {self.type} notification carries {expected.__name__} details, "
                f"got {type(self.details).__name__}"
            )
