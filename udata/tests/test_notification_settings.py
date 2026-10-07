import importlib.util
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from flask import url_for
from mongoengine import DoesNotExist, NotUniqueError
from mongoengine.connection import get_db

import udata
import udata.models  # noqa: F401 -- registers every document before the imports below
from udata.core.dataset.activities import UserUpdatedDataset
from udata.core.dataservices.factories import DataserviceFactory
from udata.core.dataset.factories import DatasetFactory
from udata.core.dataset.notifications import DatasetReusedEvent
from udata.core.discussions.factories import DiscussionFactory, MessageDiscussionFactory
from udata.core.discussions.models import Discussion
from udata.core.discussions.notifications import (
    DiscussionEvent,
    NewDiscussion,
    NewDiscussionComment,
)
from udata.core.organization.assignment import Assignment
from udata.core.organization.constants import ORG_ROLES
from udata.core.organization.factories import OrganizationFactory
from udata.core.reuse.factories import ReuseFactory
from udata.core.reuse.notifications import ReuseCreated
from udata.core.user.factories import UserFactory
from udata.features.notifications.constants import (
    ANNOUNCEMENT_TYPES,
    DEFAULT_ENABLED,
    PERSONAL_TYPES,
    REASON_BY_ORGANIZATION_ROLE,
    TYPES_REQUIRING_ACTION,
    MailCadence,
    NotificationChannel,
    NotificationReason,
    NotificationType,
)
from udata.features.notifications.events import ConfigurableEvent, configurable_events
from udata.features.notifications.mails import notification_digest
from udata.features.notifications.models import Notification
from udata.features.notifications.settings import (
    CONFIGURABLE_REASONS,
    NotificationPreference,
    NotificationSetting,
    decisions_for,
)
from udata.features.notifications.tasks import send_notification_digests
from udata.features.transfer.factories import TransferFactory
from udata.tests.api import APITestCase, PytestOnlyDBTestCase
from udata.tests.helpers import capture_mails

ALL = ConfigurableEvent.__name__
DISCUSSIONS = DiscussionEvent.__name__
REUSES_AND_DATASERVICES = DatasetReusedEvent.__name__

APP = NotificationChannel.APP
MAIL = NotificationChannel.MAIL


def decide(user, scope, event, enabled):
    return NotificationSetting.objects.create(user=user, scope=scope, event=event, enabled=enabled)


def follow(user, scope, event=ALL):
    return decide(user, scope, event, enabled=True)


def ignore(user, scope, event=ALL):
    return decide(user, scope, event, enabled=False)


def prefer(user, reason, *channels):
    return NotificationPreference.objects.create(user=user, reason=reason, channels=list(channels))


def configurable_types():
    return {event.type for event in configurable_events()}


def open_discussion(dataset):
    author = UserFactory()
    discussion = DiscussionFactory(
        subject=dataset, user=author, discussion=[MessageDiscussionFactory(posted_by=author)]
    )
    discussion.signal_new()
    return discussion


def comment(discussion):
    discussion.discussion.append(MessageDiscussionFactory())
    discussion.save()
    discussion.signal_comment(len(discussion.discussion) - 1)


def mailed(mails, user):
    return [mail for mail in mails if user.email in mail.recipients]


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
        sofia = self.login()
        organization = OrganizationFactory(editors=[sofia])
        hers = DatasetFactory(organization=organization)
        someone_elses = DatasetFactory(organization=organization)
        response = self.put(
            "/api/1/notifications/settings/",
            {
                "scope": {"class": "Dataset", "id": str(hers.id)},
                "event": DISCUSSIONS,
                "enabled": True,
            },
        )
        self.assert201(response)

        with capture_mails() as mails:
            open_discussion(hers)
            open_discussion(someone_elses)

        notifications = Notification.objects(user=sofia)
        assert notifications.count() == 1
        assert notifications.first().details.discussion.subject == hers
        assert len(mailed(mails, sofia)) == 1

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

        assert mailed(immediate, naima) == []
        assert Notification.objects(user=naima, channels=APP).count() == 2

        for notification in Notification.objects(user=naima):
            age(notification, days=8)

        with capture_mails() as weekly:
            send_notification_digests()

        assert len(mailed(weekly, naima)) == 1
        # Still readable in the bell afterwards: the digest only spends the mail channel.
        assert Notification.objects(user=naima, channels=APP).count() == 2
        assert Notification.objects(user=naima, channels=MAIL).count() == 0

    def test_an_administrator_who_never_logs_in_gets_everything_by_mail(self):
        """Gilles runs a small town's organization and never opens the site: the
        defaults alone have to serve him, without a single setting."""
        gilles = UserFactory()
        organization = OrganizationFactory(admins=[gilles])

        with capture_mails() as mails:
            open_discussion(DatasetFactory(organization=organization))

        assert NotificationSetting.objects.count() == 0
        assert NotificationPreference.objects.count() == 0
        assert mailed(mails, gilles)

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

    def test_an_outsider_can_follow_the_discussions_of_one_dataset(self):
        """Nobody in particular: not a member, not an owner, never answered. Following
        a subject has to be enough to be notified of it."""
        outsider = UserFactory()
        watched = DatasetFactory(organization=OrganizationFactory())
        other = DatasetFactory(organization=OrganizationFactory())
        follow(outsider, watched, DISCUSSIONS)

        open_discussion(watched)
        open_discussion(other)

        notifications = Notification.objects(user=outsider)
        assert notifications.count() == 1
        assert notifications.first().details.discussion.subject == watched
        assert NotificationReason.EXPLICIT_SUBSCRIBER in notifications.first().reasons

    def test_a_follower_never_hears_of_a_private_reuse_or_api(self):
        """Following a public dataset must not hand over what others keep private on
        top of it."""
        outsider = UserFactory()
        dataset = DatasetFactory(organization=OrganizationFactory())
        follow(outsider, dataset, REUSES_AND_DATASERVICES)

        ReuseFactory(datasets=[dataset], private=True)
        DataserviceFactory(datasets=[dataset], private=True)
        public = ReuseFactory(datasets=[dataset])

        notifications = Notification.objects(user=outsider)
        assert notifications.count() == 1
        assert notifications.first().details.reuse == public

    def test_followed_subjects_reach_through_the_channels_chosen_for_them(self):
        """What one follows is heard where one chose to hear it, once for all of them."""
        outsider = UserFactory()
        dataset = DatasetFactory(organization=OrganizationFactory())
        prefer(outsider, NotificationReason.EXPLICIT_SUBSCRIBER, APP)
        follow(outsider, dataset)

        with capture_mails() as mails:
            open_discussion(dataset)

        assert Notification.objects(user=outsider).count() == 1
        assert mailed(mails, outsider) == []

    def test_a_preference_follows_nothing_by_itself(self):
        """Choosing how to hear about followed subjects does not follow any."""
        outsider = UserFactory()
        prefer(outsider, NotificationReason.EXPLICIT_SUBSCRIBER, APP, MAIL)

        open_discussion(DatasetFactory(organization=OrganizationFactory()))

        assert Notification.objects(user=outsider).count() == 0

    def test_following_never_notifies_you_of_your_own_comment(self):
        author = UserFactory()
        dataset = DatasetFactory(organization=OrganizationFactory())
        discussion = DiscussionFactory(
            subject=dataset, user=author, discussion=[MessageDiscussionFactory(posted_by=author)]
        )
        follow(author, dataset)

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

    def test_a_follow_outlives_leaving_the_organization(self):
        """The other half of the rule above: what somebody asked for is theirs, and
        does not depend on a role. Discussions are public, so this grants nothing."""
        marc = UserFactory()
        organization = OrganizationFactory(editors=[marc])
        dataset = DatasetFactory(organization=organization)
        follow(marc, organization, DISCUSSIONS)

        open_discussion(dataset)
        organization.members = []
        organization.save()
        open_discussion(dataset)

        assert Notification.objects(user=marc).count() == 2

    def test_a_citizen_ignores_the_thread_they_answered_without_losing_the_others(self):
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
        ignore(claire, noisy)

        for discussion in (noisy, awaited):
            comment(discussion)

        notifications = Notification.objects(user=claire)
        assert notifications.count() == 1
        assert notifications.first().details.discussion == awaited

    def test_somebody_who_turned_everything_off_still_gets_what_needs_an_answer(self):
        """Thomas turned every reason off; an invitation he never sees would leave him
        locked out without knowing it."""
        thomas = UserFactory()
        for reason in CONFIGURABLE_REASONS:
            prefer(thomas, reason)

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
            configurable_types() | TYPES_REQUIRING_ACTION | PERSONAL_TYPES | ANNOUNCEMENT_TYPES
        ) == set(NotificationType)

    def test_the_groups_do_not_overlap(self):
        groups = [
            configurable_types(),
            set(TYPES_REQUIRING_ACTION),
            set(PERSONAL_TYPES),
            set(ANNOUNCEMENT_TYPES),
        ]
        assert sum(len(group) for group in groups) == len(set().union(*groups))

    def test_every_reason_declares_a_default(self):
        assert set(DEFAULT_ENABLED) == set(NotificationReason)

    def test_every_organization_role_maps_to_a_reason(self):
        assert set(REASON_BY_ORGANIZATION_ROLE) == set(ORG_ROLES)


class NotificationSettingModelTest(PytestOnlyDBTestCase):
    def test_one_decision_per_user_scope_and_event(self):
        user = UserFactory()
        dataset = DatasetFactory()
        ignore(user, dataset, DISCUSSIONS)

        with pytest.raises(NotUniqueError):
            follow(user, dataset, DISCUSSIONS)

    def test_the_same_scope_can_be_decided_per_event(self):
        user = UserFactory()
        dataset = DatasetFactory()
        ignore(user, dataset, DISCUSSIONS)
        follow(user, dataset, NewDiscussion.__name__)

        assert NotificationSetting.objects.count() == 2

    def test_one_preference_per_user_and_reason(self):
        user = UserFactory()
        prefer(user, NotificationReason.OWNER, APP)

        with pytest.raises(NotUniqueError):
            prefer(user, NotificationReason.OWNER, MAIL)


class ResolutionTest(PytestOnlyDBTestCase):
    def test_nothing_decided_leaves_the_user_out_of_the_decisions(self):
        user = UserFactory()

        assert decisions_for([user], NewDiscussion.decision_events(), [DatasetFactory()]) == {}

    def test_the_most_specific_scope_wins(self):
        user = UserFactory()
        organization = OrganizationFactory()
        dataset = DatasetFactory(organization=organization)
        ignore(user, dataset, DISCUSSIONS)
        follow(user, organization, DISCUSSIONS)

        decisions = decisions_for([user], NewDiscussion.decision_events(), [dataset, organization])

        assert decisions[user.id] is False

    def test_an_organization_decision_covers_its_datasets(self):
        user = UserFactory()
        organization = OrganizationFactory()
        dataset = DatasetFactory(organization=organization)
        ignore(user, organization, DISCUSSIONS)

        decisions = decisions_for([user], NewDiscussion.decision_events(), [dataset, organization])

        assert decisions[user.id] is False

    def test_a_decision_on_another_subject_does_not_leak(self):
        user = UserFactory()
        ignore(user, DatasetFactory(), DISCUSSIONS)

        decisions = decisions_for([user], NewDiscussion.decision_events(), [DatasetFactory()])

        assert decisions == {}

    def test_a_decision_on_another_family_does_not_leak(self):
        user = UserFactory()
        dataset = DatasetFactory()
        ignore(user, dataset, REUSES_AND_DATASERVICES)

        decisions = decisions_for([user], NewDiscussion.decision_events(), [dataset])

        assert decisions == {}


class DispatchTest(APITestCase):
    def test_an_editor_is_no_longer_notified_of_every_discussion(self):
        """The default that does most of the work: an editor belongs to organizations
        whose datasets they never touched."""
        editor = UserFactory()
        organization = OrganizationFactory(editors=[editor])

        open_discussion(DatasetFactory(organization=organization))

        assert Notification.objects(user=editor).count() == 0

    def test_an_editor_who_answered_keeps_hearing_about_the_thread(self):
        """Concerned twice over, as an editor and as a participant: the participant's
        default has to survive the merge with the editor's."""
        editor = UserFactory()
        dataset = DatasetFactory(organization=OrganizationFactory(editors=[editor]))
        discussion = DiscussionFactory(
            subject=dataset,
            user=UserFactory(),
            discussion=[MessageDiscussionFactory(posted_by=editor)],
        )

        comment(discussion)

        notification = Notification.objects(user=editor).get()
        assert set(notification.reasons) == {
            NotificationReason.ORGANIZATION_EDITOR,
            NotificationReason.DISCUSSION_PARTICIPANT,
        }

    def test_the_most_generous_reason_wins(self):
        """Silencing the organizations one administers does not silence the thread one
        took part in."""
        admin = UserFactory()
        dataset = DatasetFactory(organization=OrganizationFactory(admins=[admin]))
        prefer(admin, NotificationReason.ORGANIZATION_ADMIN)
        discussion = DiscussionFactory(
            subject=dataset,
            user=UserFactory(),
            discussion=[MessageDiscussionFactory(posted_by=admin)],
        )

        comment(discussion)

        assert Notification.objects(user=admin).count() == 1

    def test_an_admin_still_hears_about_discussions(self):
        admin = UserFactory()
        organization = OrganizationFactory(admins=[admin])

        open_discussion(DatasetFactory(organization=organization))

        notification = Notification.objects(user=admin).first()
        assert notification is not None
        assert NotificationReason.ORGANIZATION_ADMIN in notification.reasons
        assert notification.channels == [APP]

    def test_an_editor_can_choose_to_hear_about_every_discussion(self):
        editor = UserFactory()
        organization = OrganizationFactory(editors=[editor])
        prefer(editor, NotificationReason.ORGANIZATION_EDITOR, APP)

        open_discussion(DatasetFactory(organization=organization))

        assert Notification.objects(user=editor).count() == 1

    def test_the_bell_only_keeps_the_notification_and_skips_the_mail(self):
        admin = UserFactory()
        organization = OrganizationFactory(admins=[admin])
        prefer(admin, NotificationReason.ORGANIZATION_ADMIN, APP)

        with capture_mails() as mails:
            open_discussion(DatasetFactory(organization=organization))

        assert Notification.objects(user=admin).count() == 1
        assert mailed(mails, admin) == []

    def test_the_mail_only_drops_the_notification_and_keeps_the_mail(self):
        admin = UserFactory()
        organization = OrganizationFactory(admins=[admin])
        prefer(admin, NotificationReason.ORGANIZATION_ADMIN, MAIL)

        with capture_mails() as mails:
            open_discussion(DatasetFactory(organization=organization))

        assert Notification.objects(user=admin).count() == 0
        assert mailed(mails, admin) != []

    def test_a_type_can_be_kept_out_of_the_mails(self):
        """The new discussions by mail, not every comment: still both in the bell."""
        admin = UserFactory(mail_muted_types=[NotificationType.DISCUSSION_COMMENT])
        dataset = DatasetFactory(organization=OrganizationFactory(admins=[admin]))

        with capture_mails() as mails:
            discussion = open_discussion(dataset)
            comment(discussion)

        assert Notification.objects(user=admin).count() == 2
        assert len(mailed(mails, admin)) == 1

    def test_a_mail_one_can_turn_off_says_where_to(self):
        admin = UserFactory()
        dataset = DatasetFactory(organization=OrganizationFactory(admins=[admin]))

        with capture_mails() as mails:
            open_discussion(dataset)

        [mail] = mailed(mails, admin)
        assert "/admin/me/notifications" in mail.body

    def test_a_mail_asking_for_an_action_offers_no_way_out(self):
        """A transfer to accept is not something to turn off."""
        recipient = UserFactory()
        owner = UserFactory()

        with capture_mails() as mails:
            TransferFactory(
                user=owner,
                owner=owner,
                recipient=recipient,
                subject=DatasetFactory(owner=owner),
                status="pending",
            )

        assert all("/admin/me/notifications" not in mail.body for mail in mailed(mails, recipient))

    def test_ignoring_one_dataset_leaves_the_others_alone(self):
        admin = UserFactory()
        organization = OrganizationFactory(admins=[admin])
        ignored, other = (
            DatasetFactory(organization=organization),
            DatasetFactory(organization=organization),
        )
        ignore(admin, ignored)

        open_discussion(ignored)
        open_discussion(other)

        notifications = Notification.objects(user=admin)
        assert notifications.count() == 1
        assert notifications.first().details.discussion.subject == other

    def test_ignoring_a_single_thread(self):
        admin = UserFactory()
        organization = OrganizationFactory(admins=[admin])
        dataset = DatasetFactory(organization=organization)
        discussion = DiscussionFactory(
            subject=dataset, user=UserFactory(), discussion=[MessageDiscussionFactory()]
        )
        ignore(admin, discussion)

        discussion.signal_new()

        assert Notification.objects(user=admin).count() == 0

    def test_ignoring_the_discussions_of_a_dataset_keeps_its_reuses(self):
        owner = UserFactory()
        dataset = DatasetFactory(owner=owner)
        ignore(owner, dataset, DISCUSSIONS)

        open_discussion(dataset)
        ReuseFactory(datasets=[dataset])

        assert [notification.type for notification in Notification.objects(user=owner)] == [
            NotificationType.REUSE_CREATED
        ]

    def test_a_decision_on_the_family_covers_reuses_and_dataservices(self):
        """Both say "somebody plugged something onto your dataset", so one decision
        can cover them."""
        owner = UserFactory()
        dataset = DatasetFactory(owner=owner)
        ignore(owner, dataset, REUSES_AND_DATASERVICES)

        ReuseFactory(datasets=[dataset])
        DataserviceFactory(datasets=[dataset])

        assert Notification.objects(user=owner).count() == 0

    def test_reuses_and_dataservices_can_be_decided_apart(self):
        owner = UserFactory()
        dataset = DatasetFactory(owner=owner)
        ignore(owner, dataset, ReuseCreated.__name__)

        ReuseFactory(datasets=[dataset])
        DataserviceFactory(datasets=[dataset])

        assert [notification.type for notification in Notification.objects(user=owner)] == [
            NotificationType.DATASERVICE_CREATED
        ]

    def test_a_single_event_overrides_its_family_on_the_same_subject(self):
        """Ignoring the discussions but keeping the answers is a family decision next to
        a narrower one."""
        admin = UserFactory()
        dataset = DatasetFactory(organization=OrganizationFactory(admins=[admin]))
        ignore(admin, dataset, DISCUSSIONS)
        follow(admin, dataset, NewDiscussionComment.__name__)

        comment(open_discussion(dataset))

        assert [notification.type for notification in Notification.objects(user=admin)] == [
            NotificationType.DISCUSSION_COMMENT
        ]

    def test_the_subject_outweighs_the_event(self):
        """Ignoring one thread holds against following every comment of its dataset:
        the narrower subject is the more deliberate choice."""
        admin = UserFactory()
        dataset = DatasetFactory(organization=OrganizationFactory(admins=[admin]))
        discussion = open_discussion(dataset)
        Notification.objects(user=admin).delete()
        ignore(admin, discussion)
        follow(admin, dataset, NewDiscussionComment.__name__)

        comment(discussion)

        assert Notification.objects(user=admin).count() == 0

    def test_a_subject_can_be_followed_for_its_new_discussions_only(self):
        outsider = UserFactory()
        dataset = DatasetFactory(organization=OrganizationFactory())
        follow(outsider, dataset, NewDiscussion.__name__)

        comment(open_discussion(dataset))

        assert [notification.type for notification in Notification.objects(user=outsider)] == [
            NotificationType.DISCUSSION_NEW
        ]


class DigestTest(PytestOnlyDBTestCase):
    def test_a_digest_recipient_queues_the_mail_instead_of_receiving_it(self):
        admin = UserFactory(mail_cadence=MailCadence.WEEKLY)
        organization = OrganizationFactory(admins=[admin])

        open_discussion(DatasetFactory(organization=organization))

        notification = Notification.objects(user=admin).first()
        assert set(notification.channels) == {APP, MAIL}

    def test_muting_the_bell_still_leaves_something_to_summarize(self):
        """The case the whole `channels` field exists for: no bell, but a weekly
        recap."""
        admin = UserFactory(mail_cadence=MailCadence.WEEKLY)
        organization = OrganizationFactory(admins=[admin])
        prefer(admin, NotificationReason.ORGANIZATION_ADMIN, MAIL)

        open_discussion(DatasetFactory(organization=organization))

        notification = Notification.objects(user=admin).first()
        assert notification is not None
        assert notification.channels == [MAIL]

    def test_muting_both_channels_queues_nothing(self):
        admin = UserFactory(mail_cadence=MailCadence.WEEKLY)
        organization = OrganizationFactory(admins=[admin])
        prefer(admin, NotificationReason.ORGANIZATION_ADMIN)

        open_discussion(DatasetFactory(organization=organization))

        assert Notification.objects(user=admin).count() == 0

    def test_an_immediate_recipient_queues_nothing(self):
        admin = UserFactory(mail_cadence=MailCadence.IMMEDIATE)
        organization = OrganizationFactory(admins=[admin])

        open_discussion(DatasetFactory(organization=organization))

        assert Notification.objects(user=admin).first().channels == [APP]

    def test_the_digest_waits_for_the_cadence(self):
        admin = UserFactory(mail_cadence=MailCadence.WEEKLY)
        organization = OrganizationFactory(admins=[admin])
        open_discussion(DatasetFactory(organization=organization))

        with capture_mails() as mails:
            send_notification_digests()

        assert mails == []

    def test_the_digest_clears_the_mail_channel_and_keeps_the_bell(self):
        admin = UserFactory(mail_cadence=MailCadence.WEEKLY)
        organization = OrganizationFactory(admins=[admin])
        open_discussion(DatasetFactory(organization=organization))
        age(Notification.objects(user=admin).first(), days=8)

        send_notification_digests()

        notification = Notification.objects(user=admin).first()
        assert notification.channels == [APP]

    def test_switching_back_to_immediate_releases_the_queue(self):
        admin = UserFactory(mail_cadence=MailCadence.WEEKLY)
        organization = OrganizationFactory(admins=[admin])
        open_discussion(DatasetFactory(organization=organization))
        admin.mail_cadence = MailCadence.IMMEDIATE
        admin.save()

        with capture_mails() as mails:
            send_notification_digests()

        assert [mail.recipients for mail in mails] == [[admin.email]]
        assert Notification.objects(user=admin, channels=MAIL).count() == 0

    def test_a_daily_digest_leaves_after_a_day_and_a_weekly_one_does_not(self):
        daily = UserFactory(mail_cadence=MailCadence.DAILY)
        weekly = UserFactory(mail_cadence=MailCadence.WEEKLY)
        open_discussion(DatasetFactory(organization=OrganizationFactory(admins=[daily, weekly])))
        for notification in Notification.objects:
            age(notification, days=2)

        with capture_mails() as mails:
            send_notification_digests()

        assert [mail.recipients for mail in mails] == [[daily.email]]

    def test_the_whole_queue_leaves_as_soon_as_its_oldest_is_due(self):
        admin = UserFactory(mail_cadence=MailCadence.WEEKLY)
        organization = OrganizationFactory(admins=[admin])
        older = open_discussion(DatasetFactory(organization=organization))
        newer = open_discussion(DatasetFactory(organization=organization))
        age(Notification.objects(user=admin, details__discussion=older).first(), days=8)

        with capture_mails() as mails:
            send_notification_digests()

        [digest] = mails
        assert digest.recipients == [admin.email]
        assert digest.body.index(older.title) < digest.body.index(newer.title)
        assert Notification.objects(user=admin, channels=MAIL).count() == 0

    def test_one_failing_digest_does_not_deprive_the_others(self, caplog):
        # Two broken users, whatever order the job meets them in: the second one is only
        # reached if the job carries on after the first failure.
        broken = [UserFactory(mail_cadence=MailCadence.WEEKLY) for _ in range(2)]
        healthy = UserFactory(mail_cadence=MailCadence.WEEKLY)
        gone = [
            open_discussion(DatasetFactory(organization=OrganizationFactory(admins=[user])))
            for user in broken
        ]
        open_discussion(DatasetFactory(organization=OrganizationFactory(admins=[healthy])))
        for notification in Notification.objects:
            age(notification, days=8)
        # Removed behind the signals' back, as a raw migration would: the digest can no
        # longer read the discussion it is about.
        Discussion._get_collection().delete_many({"_id": {"$in": [d.id for d in gone]}})

        with capture_mails() as mails:
            send_notification_digests()

        assert [mail.recipients for mail in mails] == [[healthy.email]]
        assert Notification.objects(user=healthy, channels=MAIL).count() == 0
        for user in broken:
            assert Notification.objects(user=user, channels=MAIL).count() == 1
        # The trace has to reach the logs and Sentry, not only the exception message.
        failures = [record for record in caplog.records if record.levelname == "ERROR"]
        assert [failure.exc_info[0] for failure in failures] == [DoesNotExist, DoesNotExist]

    def test_a_deleted_user_gets_no_digest(self):
        """Deleting an account leaves its queue behind, and its address now ends in
        `@deleted`."""
        admin = UserFactory(mail_cadence=MailCadence.WEEKLY)
        open_discussion(DatasetFactory(organization=OrganizationFactory(admins=[admin])))
        age(Notification.objects(user=admin).first(), days=8)
        admin.mark_as_deleted(notify=False)

        with capture_mails() as mails:
            send_notification_digests()

        assert mails == []

    def test_the_digest_deletes_what_nothing_else_carries(self):
        admin = UserFactory(mail_cadence=MailCadence.WEEKLY)
        organization = OrganizationFactory(admins=[admin])
        prefer(admin, NotificationReason.ORGANIZATION_ADMIN, MAIL)
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
        assert notification.channels == [APP]

    def test_repeated_events_on_one_subject_collapse_into_a_single_line(self):
        admin = UserFactory(mail_cadence=MailCadence.WEEKLY)
        organization = OrganizationFactory(admins=[admin])
        dataset = DatasetFactory(organization=organization)
        discussion = DiscussionFactory(
            subject=dataset, user=UserFactory(), discussion=[MessageDiscussionFactory()]
        )
        discussion.signal_new()
        for _index in range(3):
            comment(discussion)

        pending = list(Notification.objects(user=admin, channels=MAIL).order_by("created_at"))
        assert len(pending) == 4

        message = notification_digest(pending)
        assert len(message.paragraphs) == 3  # intro, one line, CTA
        assert message.paragraphs[1].label == discussion.title
        assert message.paragraphs[1].content == "1 new discussion, 3 new comments"

    def test_running_the_digest_twice_sends_nothing_twice(self):
        admin = UserFactory(mail_cadence=MailCadence.WEEKLY)
        organization = OrganizationFactory(admins=[admin])
        open_discussion(DatasetFactory(organization=organization))
        age(Notification.objects(user=admin).first(), days=8)

        with capture_mails() as mails:
            send_notification_digests()
            send_notification_digests()

        assert [mail.recipients for mail in mails] == [[admin.email]]


class NotificationSettingsAPITest(APITestCase):
    def put_decision(self, enabled, scope, event=DISCUSSIONS):
        return self.put(
            "/api/1/notifications/settings/",
            {
                "scope": {"class": scope.__class__.__name__, "id": str(scope.id)}
                if scope
                else None,
                "event": event,
                "enabled": enabled,
            },
        )

    def test_deciding_again_replaces_the_previous_answer(self):
        user = self.login()
        dataset = DatasetFactory()

        self.assert201(self.put_decision(True, dataset))
        response = self.put_decision(False, dataset)

        self.assert200(response)
        listed = self.get("/api/1/notifications/settings/").json
        assert listed == [
            {
                "id": response.json["id"],
                "scope": {"class": "Dataset", "id": str(dataset.id)},
                "event": DISCUSSIONS,
                "enabled": False,
            }
        ]
        assert NotificationSetting.objects(user=user).count() == 1

    def test_withdrawing_a_decision_brings_the_reasons_back(self):
        admin = self.login()
        dataset = DatasetFactory(organization=OrganizationFactory(admins=[admin]))
        decision = self.put_decision(False, dataset).json

        self.assert204(self.delete(f"/api/1/notifications/settings/{decision['id']}/"))
        open_discussion(dataset)

        assert Notification.objects(user=admin).count() == 1

    def test_a_decision_names_a_subject(self):
        """Not deciding anything about a subject is what the preferences are for."""
        self.login()

        self.assert400(self.put_decision(False, None))

        assert NotificationSetting.objects.count() == 0

    def test_nobody_sees_nor_withdraws_the_decisions_of_somebody_else(self):
        theirs = ignore(UserFactory(), DatasetFactory())
        self.login()

        assert self.get("/api/1/notifications/settings/").json == []
        self.assert404(self.delete(f"/api/1/notifications/settings/{theirs.id}/"))
        assert NotificationSetting.objects(id=theirs.id).count() == 1

    def test_a_decision_cannot_be_scoped_to_a_user(self):
        self.login()

        response = self.put_decision(True, UserFactory())

        self.assert400(response)
        assert NotificationSetting.objects.count() == 0

    def test_a_decision_names_a_configurable_event(self):
        """An invitation is an action to take, not something to opt out of."""
        self.login()
        dataset = DatasetFactory()

        for event in ("MembershipInvited", "NotificationEvent", "Unknown"):
            self.assert400(self.put_decision(False, dataset, event=event))

        assert NotificationSetting.objects.count() == 0

    def test_a_decision_goes_with_its_subject(self):
        user = self.login()
        discussion = DiscussionFactory(subject=DatasetFactory())
        ignore(user, discussion)

        discussion.delete()

        response = self.get("/api/1/notifications/settings/")
        self.assert200(response)
        assert response.json == []

    def test_a_decision_goes_with_a_subject_purged_in_bulk(self):
        user = self.login()
        dataset = DatasetFactory()
        discussion = DiscussionFactory(subject=dataset)
        ignore(user, discussion)

        Discussion.objects(subject=dataset).delete()

        assert NotificationSetting.objects(user=user).count() == 0

    def test_settings_require_an_account(self):
        self.assert401(self.get("/api/1/notifications/settings/"))
        self.assert401(self.put_decision(True, DatasetFactory()))


class NotificationPreferencesAPITest(APITestCase):
    def test_every_configurable_reason_is_listed_with_its_defaults(self):
        self.login()

        response = self.get("/api/1/notifications/preferences/")

        self.assert200(response)
        assert {item["reason"]: item["channels"] for item in response.json} == {
            reason: sorted(NotificationChannel) if DEFAULT_ENABLED[reason] else []
            for reason in CONFIGURABLE_REASONS
        }

    def test_choosing_the_channels_of_a_reason(self):
        user = self.login()

        response = self.put(
            "/api/1/notifications/preferences/",
            {"reason": NotificationReason.ORGANIZATION_ADMIN, "channels": [APP]},
        )
        self.put(
            "/api/1/notifications/preferences/",
            {"reason": NotificationReason.ORGANIZATION_ADMIN, "channels": [MAIL]},
        )

        self.assert200(response)
        listed = {item["reason"]: item["channels"] for item in self.get("/api/1/notifications/preferences/").json}
        assert listed[NotificationReason.ORGANIZATION_ADMIN] == [MAIL]
        assert NotificationPreference.objects(user=user).count() == 1

    def test_sysadmin_notifications_are_not_configurable(self):
        self.login()

        response = self.put(
            "/api/1/notifications/preferences/",
            {"reason": NotificationReason.SYSADMIN, "channels": []},
        )

        self.assert400(response)
        assert NotificationPreference.objects.count() == 0

    def test_preferences_require_an_account(self):
        self.assert401(self.get("/api/1/notifications/preferences/"))


class MeMailSettingsAPITest(APITestCase):
    def test_the_mail_cadence_is_set_on_me_and_defers_the_mails(self):
        admin = self.login()
        organization = OrganizationFactory(admins=[admin])

        response = self.put("/api/1/me/", {"mail_cadence": MailCadence.WEEKLY})
        self.assert200(response)
        assert response.json["mail_cadence"] == MailCadence.WEEKLY

        with capture_mails() as mails:
            open_discussion(DatasetFactory(organization=organization))

        assert mailed(mails, admin) == []

    def test_the_muted_mail_types_are_set_on_me(self):
        self.login()

        response = self.put("/api/1/me/", {"mail_muted_types": [NotificationType.DISCUSSION_COMMENT]})

        self.assert200(response)
        assert response.json["mail_muted_types"] == [NotificationType.DISCUSSION_COMMENT]

    def test_the_mail_settings_of_somebody_else_are_not_disclosed(self):
        other = UserFactory(
            mail_cadence=MailCadence.WEEKLY,
            mail_muted_types=[NotificationType.DISCUSSION_COMMENT],
        )
        self.login()

        response = self.get(f"/api/1/users/{other.id}/")

        self.assert200(response)
        assert response.json["mail_cadence"] is None
        assert response.json["mail_muted_types"] is None


class NotificationReasonsAPITest(APITestCase):
    def test_the_bell_tells_why_the_user_is_concerned(self):
        admin = self.login()
        organization = OrganizationFactory(admins=[admin])
        open_discussion(DatasetFactory(organization=organization))

        response = self.get("/api/1/notifications/")

        self.assert200(response)
        assert [n["reasons"] for n in response.json["data"]] == [
            [NotificationReason.ORGANIZATION_ADMIN]
        ]


class FollowWhatOneWorksOnTest(APITestCase):
    def edit(self, dataset):
        data = dataset.to_dict()
        data["description"] = "new description"
        return self.put(url_for("api.dataset", dataset=dataset), data)

    def test_an_editor_who_edits_a_dataset_follows_it(self):
        """Sofia no longer has to follow by hand what she works on."""
        sofia = self.login()
        dataset = DatasetFactory(organization=OrganizationFactory(editors=[sofia]))

        response = self.edit(dataset)
        open_discussion(dataset)

        self.assert200(response)
        assert response.headers["X-Notification-Followed"] == f"Dataset:{dataset.id}"
        assert NotificationSetting.objects(user=sofia, scope=dataset, enabled=True).count() == 1
        assert Notification.objects(user=sofia).count() == 1

    def test_an_edit_that_follows_nothing_new_says_nothing(self):
        """Already followed: the site has nothing to announce."""
        sofia = self.login()
        dataset = DatasetFactory(organization=OrganizationFactory(editors=[sofia]))
        follow(sofia, dataset)

        response = self.edit(dataset)

        self.assert200(response)
        assert "X-Notification-Followed" not in response.headers

    def test_an_administrator_follows_too_so_as_to_keep_it_as_an_editor(self):
        admin = self.login()
        organization = OrganizationFactory(admins=[admin])
        dataset = DatasetFactory(organization=organization)

        self.assert200(self.edit(dataset))
        organization.members[0].role = "editor"
        organization.save()
        open_discussion(dataset)

        assert Notification.objects(user=admin).count() == 1

    def test_editing_what_one_ignores_keeps_it_ignored(self):
        editor = self.login()
        dataset = DatasetFactory(organization=OrganizationFactory(editors=[editor]))
        ignore(editor, dataset)

        self.assert200(self.edit(dataset))

        assert [setting.enabled for setting in NotificationSetting.objects(user=editor)] == [False]

    def test_editing_outside_of_ones_organizations_follows_nothing(self):
        """A site administrator fixing somebody else's dataset has not worked on it."""
        self.login(UserFactory(roles=["admin"]))
        dataset = DatasetFactory(organization=OrganizationFactory())

        self.assert200(self.edit(dataset))

        assert NotificationSetting.objects.count() == 0

    def test_a_script_publishing_with_an_api_key_follows_nothing(self):
        editor = UserFactory()
        dataset = DatasetFactory(organization=OrganizationFactory(editors=[editor]))

        with self.api_user(editor):
            self.assert200(self.edit(dataset))

        assert NotificationSetting.objects.count() == 0

    def test_the_followed_subjects_are_listed_with_their_organization(self):
        editor = self.login()
        organization = OrganizationFactory(editors=[editor])
        dataset = DatasetFactory(organization=organization)
        follow(editor, dataset)

        [listed] = self.get("/api/1/notifications/settings/").json

        assert listed["subject"]["title"] == dataset.title
        assert listed["subject"]["organization"]["id"] == str(organization.id)

    def test_a_subject_out_of_reach_is_listed_without_its_title(self):
        """Left the organization, and the dataset turned private since."""
        user = self.login()
        dataset = DatasetFactory(organization=OrganizationFactory(), private=True)
        follow(user, dataset)

        [listed] = self.get("/api/1/notifications/settings/").json

        assert listed["subject"] is None


class FollowEditedSubjectsMigrationTest(PytestOnlyDBTestCase):
    def migrate(self, db):
        spec = importlib.util.spec_from_file_location(
            "follow_edited_subjects",
            Path(udata.__file__).parent / "migrations" / "2026-10-06-follow-edited-subjects.py",
        )
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        migration.migrate(db)

    def test_the_members_who_edited_follow_what_they_edited(self):
        editor, left = UserFactory(), UserFactory()
        organization = OrganizationFactory(editors=[editor])
        edited, untouched = (
            DatasetFactory(organization=organization),
            DatasetFactory(organization=organization),
        )
        UserUpdatedDataset.objects.create(actor=editor, related_to=edited, organization=organization)
        UserUpdatedDataset.objects.create(actor=left, related_to=untouched, organization=organization)

        self.migrate(get_db())

        assert [(setting.user, setting.scope) for setting in NotificationSetting.objects] == [
            (editor, edited)
        ]


class DigestVisibilityTest(APITestCase):
    def test_a_mail_only_notification_is_not_listed_in_the_bell(self):
        admin = self.login()
        admin.mail_cadence = MailCadence.WEEKLY
        admin.save()
        organization = OrganizationFactory(admins=[admin])
        prefer(admin, NotificationReason.ORGANIZATION_ADMIN, MAIL)
        open_discussion(DatasetFactory(organization=organization))

        response = self.get("/api/1/notifications/")

        self.assert200(response)
        assert Notification.objects(user=admin).count() == 1
        assert response.json["data"] == []
