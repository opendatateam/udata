from datetime import UTC, datetime, timedelta

import pytest
from mongoengine import NotUniqueError

import udata.models  # noqa: F401 -- registers every document before the imports below
from udata.core.dataservices.factories import DataserviceFactory
from udata.core.dataset.factories import DatasetFactory
from udata.core.dataset.notifications import DatasetReusedEvent
from udata.core.discussions.factories import DiscussionFactory, MessageDiscussionFactory
from udata.core.discussions.notifications import DiscussionEvent
from udata.core.organization.assignment import Assignment
from udata.core.organization.constants import ORG_ROLES
from udata.core.organization.factories import OrganizationFactory
from udata.core.reuse.factories import ReuseFactory
from udata.core.user.factories import UserFactory
from udata.features.notifications.constants import (
    ANNOUNCEMENT_TYPES,
    CATEGORY_BY_TYPE,
    DEFAULT_ENABLED,
    PERSONAL_TYPES,
    REASON_BY_ORGANIZATION_ROLE,
    TYPES_REQUIRING_ACTION,
    MailCadence,
    NotificationCategory,
    NotificationChannel,
    NotificationReason,
    NotificationType,
)
from udata.features.notifications.mails import notification_digest
from udata.features.notifications.models import Notification
from udata.features.notifications.settings import (
    NotificationSetting,
    decisions_for,
    default_enabled,
)
from udata.features.notifications.tasks import send_notification_digests
from udata.features.transfer.factories import TransferFactory
from udata.tests.api import APITestCase, PytestOnlyDBTestCase
from udata.tests.helpers import capture_mails


def decide(user, category, channel, enabled, scope=None):
    return NotificationSetting.objects.create(
        user=user, scope=scope, category=category, channel=channel, enabled=enabled
    )


def mute(user, category, channel, scope=None):
    return decide(user, category, channel, enabled=False, scope=scope)


def open_discussion(dataset):
    discussion = DiscussionFactory(
        subject=dataset, user=UserFactory(), discussion=[MessageDiscussionFactory()]
    )
    discussion.signal_new()
    return discussion


def age(notification, **delta):
    """Backdate a notification so a digest considers it due."""
    Notification.objects(id=notification.id).update(
        set__created_at=datetime.now(UTC) - timedelta(**delta)
    )


class PersonaTest(APITestCase):
    """End-to-end scenarios, one per kind of person this feature exists for.

    These read as product statements rather than unit assertions on purpose: the
    classes below check that each piece behaves, these check that the pieces together
    give somebody what they asked for.
    """

    def test_an_editor_follows_two_datasets_out_of_forty(self):
        """Sofia edits a handful of datasets in a large organization and wants the
        discussions of those, not of the 38 others."""
        sofia = UserFactory()
        organization = OrganizationFactory(editors=[sofia])
        hers = DatasetFactory(organization=organization)
        someone_elses = DatasetFactory(organization=organization)
        for channel in NotificationChannel:
            decide(sofia, NotificationCategory.DISCUSSIONS, channel, enabled=True, scope=hers)

        with capture_mails() as mails:
            open_discussion(hers)
            open_discussion(someone_elses)

        notifications = Notification.objects(user=sofia)
        assert notifications.count() == 1
        assert notifications.first().details.discussion.subject == hers
        assert [mail.recipients[0] for mail in mails].count(sofia.email) == 1

    def test_an_administrator_keeps_the_bell_and_asks_for_a_weekly_recap(self):
        """Naima administers 400 datasets: everything in the bell, one mail a week."""
        naima = UserFactory(mail_cadence=MailCadence.WEEKLY)
        organization = OrganizationFactory(admins=[naima])
        first, second = (
            DatasetFactory(organization=organization),
            DatasetFactory(organization=organization),
        )

        with capture_mails() as immediate:
            open_discussion(first)
            open_discussion(second)

        assert [mail for mail in immediate if naima.email in mail.recipients] == []
        assert Notification.objects(user=naima, channels=NotificationChannel.APP).count() == 2

        for notification in Notification.objects(user=naima):
            age(notification, days=8)

        with capture_mails() as weekly:
            send_notification_digests()

        recap = [mail for mail in weekly if naima.email in mail.recipients]
        assert len(recap) == 1
        # Still readable in the bell afterwards: the digest only spends the mail channel.
        assert Notification.objects(user=naima, channels=NotificationChannel.APP).count() == 2
        assert Notification.objects(user=naima, channels=NotificationChannel.MAIL).count() == 0

    def test_an_administrator_who_never_logs_in_gets_everything_by_mail(self):
        """Gilles runs a small town's organization and never opens the site: the
        defaults alone have to serve him, without a single setting."""
        gilles = UserFactory()
        organization = OrganizationFactory(admins=[gilles])

        with capture_mails() as mails:
            open_discussion(DatasetFactory(organization=organization))

        assert NotificationSetting.objects.count() == 0
        assert [mail for mail in mails if gilles.email in mail.recipients]

    def test_a_partial_editor_hears_about_their_datasets_and_no_others(self):
        """Lea was handed two datasets in a large organization. Her scope is already
        the assignment, so she needs no setting at all — and must not receive the
        rest of the organization either."""
        lea = UserFactory()
        organization = OrganizationFactory(partial_editors=[lea])
        assigned = DatasetFactory(organization=organization)
        not_assigned = DatasetFactory(organization=organization)
        Assignment.objects.create(user=lea, organization=organization, subject=assigned)

        open_discussion(assigned)
        open_discussion(not_assigned)

        notifications = Notification.objects(user=lea)
        assert NotificationSetting.objects(user=lea).count() == 0
        assert notifications.count() == 1
        assert notifications.first().details.discussion.subject == assigned

    def test_an_outsider_can_subscribe_to_the_discussions_of_one_dataset(self):
        """Nobody in particular: not a member, not an owner, never answered. Following
        a subject has to be enough to be notified of it."""
        outsider = UserFactory()
        watched = DatasetFactory(organization=OrganizationFactory())
        ignored = DatasetFactory(organization=OrganizationFactory())
        decide(
            outsider,
            NotificationCategory.DISCUSSIONS,
            NotificationChannel.APP,
            enabled=True,
            scope=watched,
        )

        open_discussion(watched)
        open_discussion(ignored)

        notifications = Notification.objects(user=outsider)
        assert notifications.count() == 1
        assert notifications.first().details.discussion.subject == watched
        assert NotificationReason.EXPLICIT_SUBSCRIBER in notifications.first().reasons

    def test_subscribing_to_the_bell_does_not_sign_up_for_the_mails(self):
        outsider = UserFactory()
        dataset = DatasetFactory(organization=OrganizationFactory())
        decide(
            outsider,
            NotificationCategory.DISCUSSIONS,
            NotificationChannel.APP,
            enabled=True,
            scope=dataset,
        )

        with capture_mails() as mails:
            open_discussion(dataset)

        assert Notification.objects(user=outsider).count() == 1
        assert [mail for mail in mails if outsider.email in mail.recipients] == []

    def test_a_global_yes_does_not_subscribe_to_the_whole_site(self):
        """`scope=None` means "everywhere I am already concerned", not "everything"."""
        outsider = UserFactory()
        decide(outsider, NotificationCategory.DISCUSSIONS, NotificationChannel.APP, enabled=True)

        open_discussion(DatasetFactory(organization=OrganizationFactory()))

        assert Notification.objects(user=outsider).count() == 0

    def test_subscribing_never_notifies_you_of_your_own_comment(self):
        author = UserFactory()
        dataset = DatasetFactory(organization=OrganizationFactory())
        discussion = DiscussionFactory(
            subject=dataset, user=author, discussion=[MessageDiscussionFactory(posted_by=author)]
        )
        decide(
            author,
            NotificationCategory.DISCUSSIONS,
            NotificationChannel.APP,
            enabled=True,
            scope=dataset,
        )

        discussion.signal_new()

        assert Notification.objects(user=author).count() == 0

    def test_a_contributor_stops_hearing_about_an_organization_they_left(self):
        """Marc is a contractor: what he gets by virtue of his role ends with his
        access, without him having to undo anything."""
        marc = UserFactory()
        organization = OrganizationFactory(admins=[marc])
        dataset = DatasetFactory(organization=organization)

        open_discussion(dataset)
        assert Notification.objects(user=marc).count() == 1

        organization.members = []
        organization.save()
        open_discussion(dataset)

        assert NotificationSetting.objects(user=marc).count() == 0
        assert Notification.objects(user=marc).count() == 1

    def test_an_explicit_subscription_outlives_leaving_the_organization(self):
        """The other half of the rule above: what somebody asked for is theirs, and
        does not depend on a role. Discussions are public, so this grants nothing."""
        marc = UserFactory()
        organization = OrganizationFactory(editors=[marc])
        dataset = DatasetFactory(organization=organization)
        decide(
            marc,
            NotificationCategory.DISCUSSIONS,
            NotificationChannel.APP,
            enabled=True,
            scope=organization,
        )

        open_discussion(dataset)
        organization.members = []
        organization.save()
        open_discussion(dataset)

        assert Notification.objects(user=marc).count() == 2

    def test_a_citizen_mutes_the_thread_they_answered_without_losing_the_others(self):
        """Claire asked one question and does not want the whole conversation, but is
        still waiting on the other one."""
        claire = UserFactory()
        noisy = DiscussionFactory(
            subject=DatasetFactory(),
            user=UserFactory(),
            discussion=[MessageDiscussionFactory(posted_by=claire)],
        )
        awaited = DiscussionFactory(
            subject=DatasetFactory(),
            user=UserFactory(),
            discussion=[MessageDiscussionFactory(posted_by=claire)],
        )
        mute(claire, NotificationCategory.DISCUSSIONS, NotificationChannel.APP, scope=noisy)

        for discussion in (noisy, awaited):
            discussion.discussion.append(MessageDiscussionFactory())
            discussion.save()
            discussion.signal_comment(len(discussion.discussion) - 1)

        notifications = Notification.objects(user=claire)
        assert notifications.count() == 1
        assert notifications.first().details.discussion == awaited

    def test_somebody_who_turned_everything_off_still_gets_what_needs_an_answer(self):
        """Thomas unsubscribed from everything; an invitation he never sees would
        leave him locked out without knowing it."""
        thomas = UserFactory()
        for category in NotificationCategory:
            for channel in NotificationChannel:
                mute(thomas, category, channel)

        owner = UserFactory()
        TransferFactory(
            user=owner,
            owner=owner,
            recipient=thomas,
            subject=DatasetFactory(owner=owner),
            status="pending",
        )

        assert Notification.objects(user=thomas).count() == 1


class NotificationTablesTest:
    """The tables a new notification type or role has to be added to.

    None of these can be derived at import time — the event modules are loaded lazily
    to break cycles — so they are checked here, where everything is imported.
    """

    def test_every_type_is_classified(self):
        """A new type must be declared configurable, action-bound, personal or an
        announcement — deliberately, rather than by ending up unsettable by default."""
        assert (
            set(CATEGORY_BY_TYPE) | TYPES_REQUIRING_ACTION | PERSONAL_TYPES | ANNOUNCEMENT_TYPES
        ) == set(NotificationType)

    def test_the_groups_do_not_overlap(self):
        groups = [
            set(CATEGORY_BY_TYPE),
            set(TYPES_REQUIRING_ACTION),
            set(PERSONAL_TYPES),
            set(ANNOUNCEMENT_TYPES),
        ]
        assert sum(len(group) for group in groups) == len(set().union(*groups))

    def test_every_reason_declares_a_default(self):
        assert set(DEFAULT_ENABLED) == set(NotificationReason)

    def test_every_organization_role_maps_to_a_reason(self):
        assert set(REASON_BY_ORGANIZATION_ROLE) == set(ORG_ROLES)

    @pytest.mark.parametrize(
        "event_class,category",
        [
            (DiscussionEvent, NotificationCategory.DISCUSSIONS),
            (DatasetReusedEvent, NotificationCategory.REUSES),
        ],
    )
    def test_categories_match_the_event_hierarchy(self, event_class, category):
        """A category and its base event class must describe the same set of types.

        The mapping stays declarative — resolving it from the classes at import time
        would silently lose a type whose module happens not to be loaded — but the two
        are not allowed to drift.
        """
        assert {type for type, c in CATEGORY_BY_TYPE.items() if c is category} == {
            subclass.type for subclass in event_class.__subclasses__()
        }


class NotificationSettingModelTest(PytestOnlyDBTestCase):
    def test_one_decision_per_user_scope_category_and_channel(self):
        user = UserFactory()
        dataset = DatasetFactory()
        mute(user, NotificationCategory.DISCUSSIONS, NotificationChannel.MAIL, scope=dataset)

        with pytest.raises(NotUniqueError):
            mute(user, NotificationCategory.DISCUSSIONS, NotificationChannel.MAIL, scope=dataset)

    def test_the_same_scope_can_be_decided_per_channel(self):
        user = UserFactory()
        dataset = DatasetFactory()
        mute(user, NotificationCategory.DISCUSSIONS, NotificationChannel.MAIL, scope=dataset)
        mute(user, NotificationCategory.DISCUSSIONS, NotificationChannel.APP, scope=dataset)

        assert NotificationSetting.objects.count() == 2


class ResolutionTest(PytestOnlyDBTestCase):
    def test_nothing_decided_leaves_the_user_out_of_the_decisions(self):
        user = UserFactory()

        assert (
            decisions_for(
                [user],
                NotificationCategory.DISCUSSIONS,
                [DatasetFactory()],
                NotificationChannel.MAIL,
            )
            == {}
        )

    def test_the_most_specific_scope_wins(self):
        user = UserFactory()
        organization = OrganizationFactory()
        dataset = DatasetFactory(organization=organization)
        mute(user, NotificationCategory.DISCUSSIONS, NotificationChannel.MAIL, scope=dataset)
        decide(
            user,
            NotificationCategory.DISCUSSIONS,
            NotificationChannel.MAIL,
            enabled=True,
            scope=organization,
        )

        decisions = decisions_for(
            [user],
            NotificationCategory.DISCUSSIONS,
            [dataset, organization],
            NotificationChannel.MAIL,
        )

        assert decisions[user.id] is False

    def test_an_organization_decision_covers_its_datasets(self):
        user = UserFactory()
        organization = OrganizationFactory()
        dataset = DatasetFactory(organization=organization)
        mute(user, NotificationCategory.DISCUSSIONS, NotificationChannel.MAIL, scope=organization)

        decisions = decisions_for(
            [user],
            NotificationCategory.DISCUSSIONS,
            [dataset, organization],
            NotificationChannel.MAIL,
        )

        assert decisions[user.id] is False

    def test_a_global_decision_covers_everything(self):
        user = UserFactory()
        mute(user, NotificationCategory.DISCUSSIONS, NotificationChannel.MAIL)

        decisions = decisions_for(
            [user],
            NotificationCategory.DISCUSSIONS,
            [DatasetFactory()],
            NotificationChannel.MAIL,
        )

        assert decisions[user.id] is False

    def test_a_decision_on_another_subject_does_not_leak(self):
        user = UserFactory()
        mute(
            user,
            NotificationCategory.DISCUSSIONS,
            NotificationChannel.MAIL,
            scope=DatasetFactory(),
        )

        decisions = decisions_for(
            [user],
            NotificationCategory.DISCUSSIONS,
            [DatasetFactory()],
            NotificationChannel.MAIL,
        )

        assert decisions == {}

    def test_a_decision_on_another_category_does_not_leak(self):
        user = UserFactory()
        dataset = DatasetFactory()
        mute(user, NotificationCategory.REUSES, NotificationChannel.MAIL, scope=dataset)

        decisions = decisions_for(
            [user], NotificationCategory.DISCUSSIONS, [dataset], NotificationChannel.MAIL
        )

        assert decisions == {}

    def test_the_most_generous_reason_decides_the_default(self):
        """Being an editor who never opened a dataset does not cancel out having
        answered in the discussion."""
        assert default_enabled(
            {
                NotificationReason.ORGANIZATION_EDITOR,
                NotificationReason.DISCUSSION_PARTICIPANT,
            }
        )

    def test_no_reason_at_all_is_silent(self):
        assert not default_enabled(frozenset())


class DispatchTest(PytestOnlyDBTestCase):
    def test_an_editor_is_no_longer_notified_of_every_discussion(self):
        """The default that does most of the work: an editor belongs to organizations
        whose datasets they never touched."""
        editor = UserFactory()
        organization = OrganizationFactory(editors=[editor])

        open_discussion(DatasetFactory(organization=organization))

        assert Notification.objects(user=editor).count() == 0

    def test_an_admin_still_hears_about_discussions(self):
        admin = UserFactory()
        organization = OrganizationFactory(admins=[admin])

        open_discussion(DatasetFactory(organization=organization))

        notification = Notification.objects(user=admin).first()
        assert notification is not None
        assert NotificationReason.ORGANIZATION_ADMIN in notification.reasons
        assert notification.channels == [NotificationChannel.APP]

    def test_muting_the_mail_keeps_the_bell(self):
        admin = UserFactory()
        organization = OrganizationFactory(admins=[admin])
        mute(admin, NotificationCategory.DISCUSSIONS, NotificationChannel.MAIL)

        open_discussion(DatasetFactory(organization=organization))

        assert Notification.objects(user=admin).count() == 1

    def test_muting_the_bell_drops_the_notification(self):
        admin = UserFactory()
        organization = OrganizationFactory(admins=[admin])
        mute(admin, NotificationCategory.DISCUSSIONS, NotificationChannel.APP)

        open_discussion(DatasetFactory(organization=organization))

        assert Notification.objects(user=admin).count() == 0

    def test_muting_one_dataset_leaves_the_others_alone(self):
        admin = UserFactory()
        organization = OrganizationFactory(admins=[admin])
        muted, other = (
            DatasetFactory(organization=organization),
            DatasetFactory(organization=organization),
        )
        mute(admin, NotificationCategory.DISCUSSIONS, NotificationChannel.APP, scope=muted)

        open_discussion(muted)
        open_discussion(other)

        notifications = Notification.objects(user=admin)
        assert notifications.count() == 1
        assert notifications.first().details.discussion.subject == other

    def test_muting_a_single_thread(self):
        admin = UserFactory()
        organization = OrganizationFactory(admins=[admin])
        dataset = DatasetFactory(organization=organization)
        discussion = DiscussionFactory(
            subject=dataset, user=UserFactory(), discussion=[MessageDiscussionFactory()]
        )
        mute(admin, NotificationCategory.DISCUSSIONS, NotificationChannel.APP, scope=discussion)

        discussion.signal_new()

        assert Notification.objects(user=admin).count() == 0

    def test_categories_are_independent(self):
        owner = UserFactory()
        dataset = DatasetFactory(owner=owner)
        mute(owner, NotificationCategory.DISCUSSIONS, NotificationChannel.APP)

        ReuseFactory(datasets=[dataset])

        assert Notification.objects(user=owner, type=NotificationType.REUSE_CREATED).count() == 1

    def test_a_dataservice_shares_the_reuses_category(self):
        """Both say "somebody plugged something onto your dataset", so one decision
        covers them."""
        owner = UserFactory()
        dataset = DatasetFactory(owner=owner)
        mute(owner, NotificationCategory.REUSES, NotificationChannel.APP)

        DataserviceFactory(datasets=[dataset])

        assert Notification.objects(user=owner).count() == 0

    def test_a_type_without_a_category_ignores_every_setting(self):
        """Transfers, invitations and the like are actions to take, not a feed."""
        recipient = UserFactory()
        for channel in NotificationChannel:
            mute(recipient, NotificationCategory.DISCUSSIONS, channel)
            mute(recipient, NotificationCategory.REUSES, channel)

        owner = UserFactory()
        TransferFactory(
            user=owner,
            owner=owner,
            recipient=recipient,
            subject=DatasetFactory(owner=owner),
            status="pending",
        )

        assert (
            Notification.objects(user=recipient, type=NotificationType.TRANSFER_REQUESTED).count()
            == 1
        )


class DigestTest(PytestOnlyDBTestCase):
    def test_a_digest_recipient_queues_the_mail_instead_of_receiving_it(self):
        admin = UserFactory(mail_cadence=MailCadence.WEEKLY)
        organization = OrganizationFactory(admins=[admin])

        open_discussion(DatasetFactory(organization=organization))

        notification = Notification.objects(user=admin).first()
        assert set(notification.channels) == {NotificationChannel.APP, NotificationChannel.MAIL}

    def test_muting_the_bell_still_leaves_something_to_summarize(self):
        """The case the whole `channels` field exists for: no bell, but a weekly
        recap."""
        admin = UserFactory(mail_cadence=MailCadence.WEEKLY)
        organization = OrganizationFactory(admins=[admin])
        mute(admin, NotificationCategory.DISCUSSIONS, NotificationChannel.APP)

        open_discussion(DatasetFactory(organization=organization))

        notification = Notification.objects(user=admin).first()
        assert notification is not None
        assert notification.channels == [NotificationChannel.MAIL]

    def test_muting_both_channels_queues_nothing(self):
        admin = UserFactory(mail_cadence=MailCadence.WEEKLY)
        organization = OrganizationFactory(admins=[admin])
        for channel in NotificationChannel:
            mute(admin, NotificationCategory.DISCUSSIONS, channel)

        open_discussion(DatasetFactory(organization=organization))

        assert Notification.objects(user=admin).count() == 0

    def test_an_immediate_recipient_queues_nothing(self):
        admin = UserFactory(mail_cadence=MailCadence.IMMEDIATE)
        organization = OrganizationFactory(admins=[admin])

        open_discussion(DatasetFactory(organization=organization))

        assert Notification.objects(user=admin).first().channels == [NotificationChannel.APP]

    def test_the_digest_waits_for_the_cadence(self):
        admin = UserFactory(mail_cadence=MailCadence.WEEKLY)
        organization = OrganizationFactory(admins=[admin])
        open_discussion(DatasetFactory(organization=organization))

        send_notification_digests()

        notification = Notification.objects(user=admin).first()
        assert NotificationChannel.MAIL in notification.channels

    def test_the_digest_clears_the_mail_channel_and_keeps_the_bell(self):
        admin = UserFactory(mail_cadence=MailCadence.WEEKLY)
        organization = OrganizationFactory(admins=[admin])
        open_discussion(DatasetFactory(organization=organization))
        age(Notification.objects(user=admin).first(), days=8)

        send_notification_digests()

        notification = Notification.objects(user=admin).first()
        assert notification.channels == [NotificationChannel.APP]

    def test_the_digest_deletes_what_nothing_else_carries(self):
        admin = UserFactory(mail_cadence=MailCadence.WEEKLY)
        organization = OrganizationFactory(admins=[admin])
        mute(admin, NotificationCategory.DISCUSSIONS, NotificationChannel.APP)
        open_discussion(DatasetFactory(organization=organization))
        age(Notification.objects(user=admin).first(), days=8)

        send_notification_digests()

        assert Notification.objects(user=admin).count() == 0

    def test_a_type_that_never_mails_is_not_queued(self):
        """A reuse creation has no `via_mail`, so going weekly must not conjure a mail
        the immediate path never sends."""
        owner = UserFactory(mail_cadence=MailCadence.WEEKLY)
        dataset = DatasetFactory(owner=owner)

        ReuseFactory(datasets=[dataset])

        notification = Notification.objects(user=owner).first()
        assert notification.channels == [NotificationChannel.APP]

    def test_repeated_events_on_one_subject_collapse_into_a_single_line(self):
        admin = UserFactory(mail_cadence=MailCadence.WEEKLY)
        organization = OrganizationFactory(admins=[admin])
        dataset = DatasetFactory(organization=organization)
        discussion = DiscussionFactory(
            subject=dataset, user=UserFactory(), discussion=[MessageDiscussionFactory()]
        )
        discussion.signal_new()
        for _index in range(3):
            message = MessageDiscussionFactory()
            discussion.discussion.append(message)
            discussion.save()
            discussion.signal_comment(len(discussion.discussion) - 1)

        pending = list(Notification.objects(user=admin, channels=NotificationChannel.MAIL))
        assert len(pending) == 4

        message = notification_digest(pending)
        assert len(message.paragraphs) == 3  # intro, one line, CTA
        assert "3" in message.paragraphs[1].content
        assert "1" in message.paragraphs[1].content

    def test_running_the_digest_twice_sends_nothing_twice(self):
        admin = UserFactory(mail_cadence=MailCadence.WEEKLY)
        organization = OrganizationFactory(admins=[admin])
        open_discussion(DatasetFactory(organization=organization))
        age(Notification.objects(user=admin).first(), days=8)

        send_notification_digests()
        send_notification_digests()

        notification = Notification.objects(user=admin).first()
        assert NotificationChannel.MAIL not in notification.channels


class DigestVisibilityTest(APITestCase):
    def test_a_mail_only_notification_is_not_listed_in_the_bell(self):
        admin = self.login()
        admin.mail_cadence = MailCadence.WEEKLY
        admin.save()
        organization = OrganizationFactory(admins=[admin])
        mute(admin, NotificationCategory.DISCUSSIONS, NotificationChannel.APP)
        open_discussion(DatasetFactory(organization=organization))

        response = self.get("/api/1/notifications/")

        self.assert200(response)
        assert Notification.objects(user=admin).count() == 1
        assert response.json["data"] == []
