import factory

from udata.core.user.factories import UserFactory
from udata.factories import ModelFactory
from udata.features.notifications.constants import NotificationType
from udata.features.notifications.models import Notification

from .models import Member, Organization, Team
from .notifications import MembershipRequestNotificationDetails


class OrganizationFactory(ModelFactory):
    class Meta:
        model = Organization

    name = factory.Faker("sentence")
    description = factory.Faker("text")
    members = factory.LazyAttribute(
        lambda o: (
            [Member(user=user, role="admin") for user in o.admins]
            + [Member(user=user, role="editor") for user in o.editors]
            + [Member(user=user, role="partial_editor") for user in o.partial_editors]
        )
    )

    class Params:
        admins = []
        editors = []
        partial_editors = []


class TeamFactory(ModelFactory):
    class Meta:
        model = Team

    name = factory.Faker("sentence")


class MembershipRequestNotificationFactory(ModelFactory):
    class Meta:
        model = Notification
        exclude = ("request_organization", "request_user")

    user = factory.SubFactory(UserFactory)
    type = NotificationType.ORGANIZATION_MEMBERSHIP_REQUESTED
    details = factory.LazyAttribute(
        lambda o: MembershipRequestNotificationDetails(
            request_organization=o.request_organization, request_user=o.request_user
        )
    )
    request_organization = factory.SubFactory(OrganizationFactory)
    request_user = factory.SubFactory(UserFactory)

    class Params:
        invitation = factory.Trait(type=NotificationType.ORGANIZATION_MEMBERSHIP_INVITED)
