from mongoengine import EmbeddedDocument
from mongoengine.fields import ReferenceField

from udata.api_fields import field, generate_fields
from udata.core.organization import mails
from udata.core.organization.constants import (
    ASSOCIATION,
    CERTIFIED,
    COMPANY,
    LOCAL_AUTHORITY,
    PUBLIC_SERVICE,
)
from udata.core.organization.models import MembershipRequest, Organization
from udata.core.user.models import User
from udata.features.notifications.constants import NotificationReason, NotificationType
from udata.features.notifications.events import (
    NotificationEvent,
    Recipient,
    responsible_recipients,
)
from udata.i18n import lazy_gettext as _

BADGE_NOTIFICATION_TYPES = {
    CERTIFIED: NotificationType.ORGANIZATION_BADGE_CERTIFIED,
    PUBLIC_SERVICE: NotificationType.ORGANIZATION_BADGE_PUBLIC_SERVICE,
    COMPANY: NotificationType.ORGANIZATION_BADGE_COMPANY,
    ASSOCIATION: NotificationType.ORGANIZATION_BADGE_ASSOCIATION,
    LOCAL_AUTHORITY: NotificationType.ORGANIZATION_BADGE_LOCAL_AUTHORITY,
}

BADGE_MAILS = {
    CERTIFIED: mails.badge_added_certified,
    PUBLIC_SERVICE: mails.badge_added_public_service,
    COMPANY: mails.badge_added_company,
    ASSOCIATION: mails.badge_added_association,
    LOCAL_AUTHORITY: mails.badge_added_local_authority,
}


@generate_fields()
class MembershipRequestNotificationDetails(EmbeddedDocument):
    types = frozenset(
        {
            NotificationType.ORGANIZATION_MEMBERSHIP_REQUESTED,
            NotificationType.ORGANIZATION_MEMBERSHIP_INVITED,
        }
    )

    request_organization = field(
        ReferenceField(Organization),
        readonly=True,
        nested_fields=Organization.__ref_fields__,
        auditable=False,
        allow_null=True,
        filterable={},
    )
    request_user = field(
        ReferenceField(User),
        readonly=True,
        auditable=False,
        allow_null=True,
        filterable={},
    )


@generate_fields()
class NewBadgeNotificationDetails(EmbeddedDocument):
    types = frozenset(BADGE_NOTIFICATION_TYPES.values())

    organization = field(
        ReferenceField(Organization),
        readonly=True,
        nested_fields=Organization.__ref_fields__,
        auditable=False,
        allow_null=True,
        filterable={},
    )


@generate_fields()
class MembershipAcceptedNotificationDetails(EmbeddedDocument):
    types = frozenset({NotificationType.ORGANIZATION_MEMBERSHIP_ACCEPTED})

    organization = field(
        ReferenceField(Organization),
        readonly=True,
        nested_fields=Organization.__ref_fields__,
        auditable=False,
        allow_null=True,
        filterable={},
    )


@generate_fields()
class MembershipRefusedNotificationDetails(EmbeddedDocument):
    types = frozenset({NotificationType.ORGANIZATION_MEMBERSHIP_REFUSED})

    organization = field(
        ReferenceField(Organization),
        readonly=True,
        nested_fields=Organization.__ref_fields__,
        auditable=False,
        allow_null=True,
        filterable={},
    )


class BadgeAdded(NotificationEvent):
    """The whole organization hears about a badge it was awarded.

    One class for the five badge types: they differ only by the type they carry and
    the email they send, both looked up from the badge kind.
    """

    types = frozenset(BADGE_NOTIFICATION_TYPES.values())
    label = _("Badges of the organization")

    def __init__(self, organization: Organization, kind: str):
        self.organization = organization
        self.kind = kind
        self.type = BADGE_NOTIFICATION_TYPES[kind]

    @property
    def subject(self):
        return self.organization

    def recipients(self):
        return responsible_recipients(self.organization)

    def via_app(self, recipient):
        return NewBadgeNotificationDetails(organization=self.organization)

    def via_mail(self, recipient):
        return BADGE_MAILS[self.kind](self.organization)


class MembershipRequested(NotificationEvent):
    """Only admins can answer a membership request, so only they are asked to."""

    type = NotificationType.ORGANIZATION_MEMBERSHIP_REQUESTED

    def __init__(self, organization: Organization, request: MembershipRequest):
        self.organization = organization
        self.request = request

    @property
    def occurred_at(self):
        return self.request.created

    def recipients(self):
        return [Recipient.from_member(member) for member in self.organization.by_role("admin")]

    def via_app(self, recipient):
        if self.already_pending(
            recipient,
            request_organization=self.organization,
            request_user=self.request.user,
        ):
            return None
        return MembershipRequestNotificationDetails(
            request_organization=self.organization,
            request_user=self.request.user,
        )

    def via_mail(self, recipient):
        return mails.new_membership_request(self.organization, self.request)


class MembershipInvited(MembershipRequested):
    """An invitation is answered by the invited user, not by the admins."""

    type = NotificationType.ORGANIZATION_MEMBERSHIP_INVITED

    def recipients(self):
        # An invitation may target an address that has no account yet: it then has a
        # mail channel and no in-app one, since there is no user to notify.
        # No reason to carry: being the person invited is what the type already says.
        return [Recipient(self.request.user or self.request.email)]

    def via_mail(self, recipient):
        return mails.membership_invitation(
            self.organization, self.request, user_exists=isinstance(recipient, User)
        )


class MembershipInvitationMatched(MembershipInvited):
    """A pending email invitation just got attached to an account owning its address.

    The invitation mail went out when it was created, to an address that had no account
    to hang a notification on: registering or changing one's email only makes the
    invitation reachable in-app.
    """

    def via_mail(self, recipient):
        return None


class MembershipAnswered(NotificationEvent):
    """The applicant hears back about their own request."""

    reaches_subscribers = False

    def __init__(self, organization: Organization, request: MembershipRequest):
        self.organization = organization
        self.request = request

    @property
    def subject(self):
        return self.organization

    def recipients(self):
        return [Recipient(self.request.user, frozenset({NotificationReason.REQUESTER}))]


class MembershipAccepted(MembershipAnswered):
    type = NotificationType.ORGANIZATION_MEMBERSHIP_ACCEPTED
    label = _("Accepted memberships")

    def via_app(self, recipient):
        return MembershipAcceptedNotificationDetails(organization=self.organization)

    def via_mail(self, recipient):
        return mails.membership_accepted(self.organization)


class MembershipRefused(MembershipAnswered):
    type = NotificationType.ORGANIZATION_MEMBERSHIP_REFUSED
    label = _("Refused memberships")

    def via_app(self, recipient):
        return MembershipRefusedNotificationDetails(organization=self.organization)

    def via_mail(self, recipient):
        return mails.membership_refused(self.organization)


@MembershipRequest.after_handle.connect
def on_handle_membership_request(request: MembershipRequest, **kwargs):
    from udata.features.notifications.models import Notification

    organization = kwargs.get("org")

    if organization is None:
        return

    Notification.objects(
        details__request_organization=organization,
        details__request_user=request.user,
    ).mark_handled(at=request.handled_on)
