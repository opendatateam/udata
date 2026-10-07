from collections.abc import Callable

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
from udata.mail import MailMessage



@generate_fields()
class MembershipRequestNotificationDetails(EmbeddedDocument):
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

    One subclass per badge, declaring its type on the class like every other event, so
    that the type alone finds the event (see `event_for_type`). They differ only by that
    type and the email they send.
    """

    badge_mail: Callable[[Organization], MailMessage]

    def __init__(self, organization: Organization):
        self.organization = organization

    @property
    def subject(self):
        return self.organization

    def recipients(self):
        return responsible_recipients(self.organization)

    def scopes(self):
        return [self.organization]

    def via_app(self, recipient):
        return NewBadgeNotificationDetails(organization=self.organization)

    def via_mail(self, recipient):
        return self.badge_mail(self.organization)


class CertifiedBadgeAdded(BadgeAdded):
    type = NotificationType.ORGANIZATION_BADGE_CERTIFIED
    badge_mail = staticmethod(mails.badge_added_certified)


class PublicServiceBadgeAdded(BadgeAdded):
    type = NotificationType.ORGANIZATION_BADGE_PUBLIC_SERVICE
    badge_mail = staticmethod(mails.badge_added_public_service)


class CompanyBadgeAdded(BadgeAdded):
    type = NotificationType.ORGANIZATION_BADGE_COMPANY
    badge_mail = staticmethod(mails.badge_added_company)


class AssociationBadgeAdded(BadgeAdded):
    type = NotificationType.ORGANIZATION_BADGE_ASSOCIATION
    badge_mail = staticmethod(mails.badge_added_association)


class LocalAuthorityBadgeAdded(BadgeAdded):
    type = NotificationType.ORGANIZATION_BADGE_LOCAL_AUTHORITY
    badge_mail = staticmethod(mails.badge_added_local_authority)


BADGE_EVENTS: dict[str, type[BadgeAdded]] = {
    CERTIFIED: CertifiedBadgeAdded,
    PUBLIC_SERVICE: PublicServiceBadgeAdded,
    COMPANY: CompanyBadgeAdded,
    ASSOCIATION: AssociationBadgeAdded,
    LOCAL_AUTHORITY: LocalAuthorityBadgeAdded,
}


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

    def __init__(self, organization: Organization, request: MembershipRequest):
        self.organization = organization
        self.request = request

    @property
    def subject(self):
        return self.organization

    def recipients(self):
        return [Recipient(self.request.user, frozenset({NotificationReason.REQUESTER}))]

    def scopes(self):
        return [self.organization]


class MembershipAccepted(MembershipAnswered):
    type = NotificationType.ORGANIZATION_MEMBERSHIP_ACCEPTED

    def via_app(self, recipient):
        return MembershipAcceptedNotificationDetails(organization=self.organization)

    def via_mail(self, recipient):
        return mails.membership_accepted(self.organization)


class MembershipRefused(MembershipAnswered):
    type = NotificationType.ORGANIZATION_MEMBERSHIP_REFUSED

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
