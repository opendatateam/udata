from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from flask import url_for
from mongoengine import DoesNotExist, NotUniqueError, ValidationError

import udata
import udata.features.notifications.follow  # noqa: F401 -- connected by `init_app` in production
import udata.models  # noqa: F401 -- registers every document before the imports below
from udata.core.dataservices.factories import DataserviceFactory
from udata.core.dataset.factories import DatasetFactory, ResourceFactory
from udata.core.discussions.factories import DiscussionFactory, MessageDiscussionFactory
from udata.core.discussions.models import Discussion
from udata.core.organization.assignment import Assignment
from udata.core.organization.constants import CERTIFIED, ORG_ROLES
from udata.core.organization.factories import OrganizationFactory
from udata.core.organization.models import MembershipRequest
from udata.core.reuse.factories import ReuseFactory
from udata.core.user.factories import AdminFactory, UserFactory
from udata.features.notifications.constants import (
    REASON_BY_ORGANIZATION_ROLE,
    FollowOrigin,
    MailCadence,
    NotificationChannel,
    NotificationReason,
    NotificationType,
)
from udata.features.notifications.events import event_for_type, is_event_name
from udata.features.notifications.mails import notification_digest
from udata.features.notifications.models import SCOPE_MODELS, Notification
from udata.features.notifications.settings import (
    DEFAULT_RULES,
    NOTIFICATION_SCOPES,
    NotificationSetting,
    Rule,
    resolve,
    rules_for,
)
from udata.features.notifications.tasks import send_notification_digests
from udata.features.transfer.factories import TransferFactory
from udata.tests.api import APITestCase, PytestOnlyDBTestCase
from udata.tests.helpers import capture_mails

DISCUSSIONS = "discussion"

APP = NotificationChannel.APP
MAIL = NotificationChannel.MAIL


def decide(user, scope=None, event=None, enabled=True, **kwargs):
    return NotificationSetting.objects.create(
        user=user,
        scope=scope,
        event=event,
        enabled=enabled,
        **kwargs,
    )


def follow(user, scope, event=None):
    return decide(user, scope, event, enabled=True)


def ignore(user, scope, event=None):
    return decide(user, scope, event, enabled=False)


def turn_everything_off(user):
    user.notifications_paused = True
    user.save()


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


def ref(subject):
    return {"class": subject.__class__.__name__, "id": str(subject.id)}


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
        self.login(sofia)
        response = self.put(
            "/api/1/notifications/settings/",
            {"scope": ref(hers), "event": DISCUSSIONS, "enabled": True},
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
        follow(outsider, dataset)

        ReuseFactory(datasets=[dataset], private=True)
        DataserviceFactory(datasets=[dataset], private=True)
        public = ReuseFactory(datasets=[dataset])

        notifications = Notification.objects(user=outsider)
        assert notifications.count() == 1
        assert notifications.first().details.reuse == public

    def test_following_an_organization_does_not_disclose_its_private_datasets(self):
        """Anybody can follow an organization: what it keeps private must not reach them
        through the discussions about it."""
        outsider = UserFactory()
        organization = OrganizationFactory()
        follow(outsider, organization)

        with capture_mails() as mails:
            open_discussion(DatasetFactory(organization=organization, private=True))

        assert Notification.objects(user=outsider).count() == 0
        assert mailed(mails, outsider) == []

    def test_a_rule_without_a_subject_follows_nothing_by_itself(self):
        """Saying yes to the discussions everywhere is everywhere one is already
        concerned, not the discussions of the whole site."""
        outsider = UserFactory()
        decide(outsider, event=DISCUSSIONS, enabled=True)

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

    def test_turning_everything_off_silences_even_what_one_follows(self):
        """ "Turn everything off" means it: a follow, however precise, does not bring
        anything back."""
        thomas = UserFactory()
        dataset = DatasetFactory(organization=OrganizationFactory(admins=[thomas]))
        turn_everything_off(thomas)
        follow(thomas, dataset)

        with capture_mails() as mails:
            open_discussion(dataset)

        assert Notification.objects(user=thomas).count() == 0
        assert mailed(mails, thomas) == []

    def test_a_request_to_answer_reaches_an_admin_who_said_no_to_everything(self):
        """Saying no to every notification everywhere still leaves the requests to join
        one's organization: unanswered, they would sit there with nobody knowing."""
        admin = UserFactory()
        organization = OrganizationFactory(admins=[admin])
        decide(admin, enabled=False)
        self.login()

        with capture_mails() as mails:
            self.post(url_for("api.request_membership", org=organization), {"comment": "x"})

        assert Notification.objects(user=admin).count() == 1
        assert len(mailed(mails, admin)) == 1

    def test_turning_everything_off_still_leaves_what_needs_an_answer(self):
        thomas = UserFactory()
        turn_everything_off(thomas)

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
    """The tables a new notification type or role has to be added to, checked here,
    where everything is imported."""

    def test_every_type_finds_the_event_that_sends_it(self):
        """The digest goes from a stored type back to its event: a type no event
        declares, like one set on an instance only, cannot be summarized."""
        for notification_type in NotificationType:
            event = event_for_type(notification_type)
            declared = event.types if hasattr(event, "types") else {event.type}
            assert notification_type in declared

    def test_every_organization_role_maps_to_a_reason(self):
        assert set(REASON_BY_ORGANIZATION_ROLE) == set(ORG_ROLES)

    def test_every_default_rule_names_a_real_event(self):
        assert all(rule.event is None or is_event_name(rule.event) for rule in DEFAULT_RULES)

    def test_every_scope_takes_its_rules_along_when_deleted(self):
        """A scope missing from the cleanup leaves rules no one can list nor withdraw."""
        assert {model.__name__ for model in SCOPE_MODELS} == set(NOTIFICATION_SCOPES)


class EventNameTest:
    def test_a_type_and_its_prefixes_are_event_names(self):
        assert is_event_name("discussion.comment")
        assert is_event_name("discussion")
        assert is_event_name("organization.badge")

    def test_a_partial_word_is_not_a_prefix(self):
        assert not is_event_name("discuss")
        assert not is_event_name("discussion.comm")

    def test_class_names_are_not_event_names(self):
        assert not is_event_name("NewDiscussion")
        assert not is_event_name("Unknown")


class NotificationSettingModelTest(PytestOnlyDBTestCase):
    def test_one_rule_per_user_scope_and_event(self):
        user = UserFactory()
        dataset = DatasetFactory()
        ignore(user, dataset, DISCUSSIONS)

        with pytest.raises(NotUniqueError):
            follow(user, dataset, DISCUSSIONS)

    def test_the_same_scope_can_be_decided_per_event(self):
        user = UserFactory()
        dataset = DatasetFactory()
        ignore(user, dataset, DISCUSSIONS)
        follow(user, dataset, NotificationType.DISCUSSION_NEW)

        assert NotificationSetting.objects.count() == 2

    def test_a_rule_names_a_type_or_a_prefix_of_one(self):
        user = UserFactory()

        for event in ("NewDiscussion", "Unknown", "discuss"):
            with pytest.raises(ValidationError):
                decide(user, event=event, enabled=False)

        assert NotificationSetting.objects.count() == 0

    def test_a_rule_is_set_by_hand_unless_told_otherwise(self):
        assert follow(UserFactory(), DatasetFactory()).origin == FollowOrigin.FOLLOWED


THREAD, DATASET, ORGANIZATION = (SimpleNamespace(id=name) for name in ("t", "d", "o"))
SCOPES = [THREAD, DATASET, ORGANIZATION]
NEW = ["discussion.new", "discussion"]
COMMENT = ["discussion.comment", "discussion"]


def rule(scope=None, event=None, enabled=True):
    return Rule(enabled=enabled, scope=scope.id if scope else None, event=event)


class ResolveTest:
    """`resolve` alone, on the cases the settings were designed around: which rule wins
    when several apply."""

    def test_the_defaults_alone(self):
        assert resolve([], NEW, SCOPES, {NotificationReason.ORGANIZATION_ADMIN}) is True
        assert resolve([], NEW, SCOPES, {NotificationReason.ORGANIZATION_EDITOR}) is False

    def test_a_new_reason_is_heard_by_default(self):
        """No reason but the editors' is silenced by default, so that forgetting one
        cannot silence it."""
        for reason in set(NotificationReason) - {NotificationReason.ORGANIZATION_EDITOR}:
            assert resolve([], NEW, SCOPES, {reason}) is True

    def test_editors_hear_about_the_badges_of_their_organization(self):
        assert resolve(
            [], ["organization.badge.certified", "organization.badge", "organization"],
            [ORGANIZATION], {NotificationReason.ORGANIZATION_EDITOR},
        ) is True  # fmt: skip

    def test_following_a_dataset_beats_the_default_of_editors(self):
        rules = [rule(scope=DATASET)]

        assert resolve(rules, NEW, SCOPES, {NotificationReason.ORGANIZATION_EDITOR}) is True

    def test_an_event_on_a_thread_beats_the_thread(self):
        rules = [rule(scope=THREAD, enabled=False), rule(scope=THREAD, event="discussion.comment")]

        assert resolve(rules, COMMENT, SCOPES, {NotificationReason.ORGANIZATION_ADMIN}) is True

    def test_the_most_generous_reason_wins(self):
        """Silenced as an editor by default, heard as a participant of the thread."""
        reasons = {
            NotificationReason.ORGANIZATION_EDITOR,
            NotificationReason.DISCUSSION_PARTICIPANT,
        }

        assert resolve([], COMMENT, SCOPES, reasons) is True

    def test_a_choice_on_an_event_beats_the_default_of_a_reason(self):
        rules = [rule(event="discussion.new")]

        assert resolve(rules, NEW, SCOPES, {NotificationReason.ORGANIZATION_EDITOR}) is True

    def test_ignoring_a_dataset(self):
        rules = [rule(scope=DATASET, enabled=False)]

        assert resolve(rules, NEW, SCOPES, {NotificationReason.ORGANIZATION_ADMIN}) is False

    def test_the_users_broad_choice_beats_a_precise_default(self):
        """Defaults are only read where the user said nothing: "editors, yes" set by the
        user is not undone by the narrower default of the badges."""
        rules = [rule(enabled=False)]

        assert resolve(
            rules, ["organization.badge.certified", "organization.badge", "organization"],
            [ORGANIZATION], {NotificationReason.ORGANIZATION_EDITOR},
        ) is False  # fmt: skip

    def test_rules_about_other_subjects_or_events_are_ignored(self):
        rules = [
            rule(scope=SimpleNamespace(id="elsewhere"), enabled=False),
            rule(event="reuse.created", enabled=False),
        ]

        assert resolve(rules, NEW, SCOPES, {NotificationReason.ORGANIZATION_ADMIN}) is True

    def test_nobody_concerned_gets_nothing(self):
        assert resolve([rule(scope=DATASET)], NEW, SCOPES, set()) is False

    def test_a_participant_is_not_silenced_by_a_rule_on_the_organization(self):
        """Taking part in a thread is following it: "only what I follow" on the
        organization keeps it."""
        rules = [rule(scope=ORGANIZATION, enabled=False)]

        assert resolve(rules, COMMENT, SCOPES, {NotificationReason.DISCUSSION_PARTICIPANT}) is True

    def test_a_participant_can_still_ignore_the_thread(self):
        rules = [rule(scope=THREAD, enabled=False)]

        assert resolve(rules, COMMENT, SCOPES, {NotificationReason.DISCUSSION_PARTICIPANT}) is False


class RulesForTest(PytestOnlyDBTestCase):
    def test_nothing_decided_leaves_the_user_out(self):
        assert rules_for([UserFactory()], NEW, [DatasetFactory()]) == {}

    def test_only_the_rules_that_can_apply_are_loaded(self):
        user = UserFactory()
        dataset = DatasetFactory()
        ignore(user, dataset, DISCUSSIONS)
        ignore(user, DatasetFactory(), DISCUSSIONS)
        ignore(user, dataset, NotificationType.REUSE_CREATED)
        decide(user, enabled=False)

        rules = rules_for([user], NEW, [dataset])[user.id]

        assert sorted(rules, key=lambda rule: rule.scope is None) == [
            Rule(enabled=False, scope=dataset.id, event=DISCUSSIONS),
            Rule(enabled=False),
        ]

    def test_an_organization_rule_covers_its_datasets(self):
        user = UserFactory()
        organization = OrganizationFactory()
        dataset = DatasetFactory(organization=organization)
        ignore(user, organization, DISCUSSIONS)

        rules = rules_for([user], NEW, [dataset, organization])[user.id]

        assert resolve(rules, NEW, [dataset, organization], {NotificationReason.OWNER}) is False

    def test_the_most_specific_scope_wins(self):
        user = UserFactory()
        organization = OrganizationFactory()
        dataset = DatasetFactory(organization=organization)
        ignore(user, dataset, DISCUSSIONS)
        follow(user, organization, DISCUSSIONS)

        rules = rules_for([user], NEW, [dataset, organization])[user.id]

        assert resolve(rules, NEW, [dataset, organization], {NotificationReason.OWNER}) is False


class DispatchTest(APITestCase):
    def test_an_editor_is_no_longer_notified_of_every_discussion(self):
        """The default that does most of the work: an editor belongs to organizations
        whose datasets they never touched."""
        editor = UserFactory()
        organization = OrganizationFactory(editors=[editor])

        open_discussion(DatasetFactory(organization=organization))

        assert Notification.objects(user=editor).count() == 0

    def test_an_editor_still_hears_about_the_badges_of_their_organization(self):
        editor = UserFactory()
        organization = OrganizationFactory(editors=[editor])

        organization.add_badge(CERTIFIED)

        notification = Notification.objects(user=editor).get()
        assert notification.reasons == [NotificationReason.ORGANIZATION_EDITOR]

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

    def test_an_admin_still_hears_about_discussions(self):
        admin = UserFactory()
        organization = OrganizationFactory(admins=[admin])

        open_discussion(DatasetFactory(organization=organization))

        notification = Notification.objects(user=admin).first()
        assert notification is not None
        assert NotificationReason.ORGANIZATION_ADMIN in notification.reasons
        assert notification.channels == [APP]

    @pytest.mark.options(CDATA_BASE_URL="https://www.data.gouv.fr", DEFAULT_LANGUAGE="en")
    def test_a_mail_one_can_turn_off_says_why_and_where_to(self):
        admin = UserFactory()
        organization = OrganizationFactory(admins=[admin])
        dataset = DatasetFactory(organization=organization)

        with capture_mails() as mails:
            open_discussion(dataset)

        [mail] = mailed(mails, admin)
        assert "/admin/me/notifications" in mail.body
        assert f"you administer {organization.name}" in mail.body

    @pytest.mark.options(CDATA_BASE_URL="https://www.data.gouv.fr", DEFAULT_LANGUAGE="en")
    def test_a_mail_offers_the_ways_out_of_the_bell(self):
        """The thread, its subject and the type, each a link the settings page confirms."""
        admin = UserFactory()
        dataset = DatasetFactory(organization=OrganizationFactory(admins=[admin]))

        with capture_mails() as mails:
            discussion = open_discussion(dataset)

        [mail] = mailed(mails, admin)
        settings = "https://www.data.gouv.fr/admin/me/notifications"
        assert (
            f"Stop following this discussion: {settings}?scope=Discussion%3A{discussion.id}&event=discussion"
            in mail.body
        )
        assert (
            f"Receive nothing more about {dataset.title}: {settings}?scope=Dataset%3A{dataset.id}"
            in mail.body
        )
        assert (
            f"Stop receiving this type of notification: {settings}?event=discussion.new"
            in mail.body
        )

    @pytest.mark.options(CDATA_BASE_URL="https://www.data.gouv.fr", DEFAULT_LANGUAGE="en")
    def test_a_badge_mail_offers_its_organization_and_its_type(self):
        admin = UserFactory()
        organization = OrganizationFactory(admins=[admin])

        with capture_mails() as mails:
            organization.add_badge(CERTIFIED)

        [mail] = mailed(mails, admin)
        assert f"scope=Organization%3A{organization.id}" in mail.body
        assert "event=organization.badge.certified" in mail.body
        assert "Stop following this discussion" not in mail.body

    @pytest.mark.options(DEFAULT_LANGUAGE="en")
    def test_a_title_in_the_footer_is_escaped(self):
        """A title is chosen by whoever publishes, and the mail leaves from the platform."""
        follower = UserFactory()
        dataset = DatasetFactory(organization=OrganizationFactory(), title="<b>x</b>")
        follow(follower, dataset)

        with capture_mails() as mails:
            open_discussion(dataset)

        [mail] = mailed(mails, follower)
        assert "<b>x</b>" not in mail.html
        assert "you follow <b>x</b>" in mail.body

    @pytest.mark.options(DEFAULT_LANGUAGE="en")
    def test_a_mail_names_every_reason(self):
        """Naming only one would offer a way out that stops nothing."""
        admin = UserFactory()
        organization = OrganizationFactory(admins=[admin])
        discussion = DiscussionFactory(
            subject=DatasetFactory(organization=organization),
            user=UserFactory(),
            discussion=[MessageDiscussionFactory(posted_by=admin)],
        )

        with capture_mails() as mails:
            comment(discussion)

        [mail] = mailed(mails, admin)
        assert f"you administer {organization.name}" in mail.body
        assert "you take part in this discussion" in mail.body

    @pytest.mark.options(CDATA_BASE_URL="https://www.data.gouv.fr")
    def test_a_mail_asking_for_an_action_offers_no_way_out(self):
        """A membership request to answer is not something to turn off."""
        admin = UserFactory()
        organization = OrganizationFactory(admins=[admin])
        self.login()

        with capture_mails() as mails:
            self.post(url_for("api.request_membership", org=organization), {"comment": "x"})

        [mail] = mailed(mails, admin)
        assert "/admin/me/notifications" not in mail.body

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

    def test_an_answer_to_a_request_only_reaches_the_applicant(self):
        """Following an organization is not being told "your request was accepted"
        every time somebody joins it."""
        admin, applicant, follower = UserFactory(), UserFactory(), UserFactory()
        request = MembershipRequest(user=applicant, comment="x")
        organization = OrganizationFactory(admins=[admin], requests=[request])
        follow(follower, organization)
        self.login(admin)

        with capture_mails() as mails:
            self.post(url_for("api.accept_membership", org=organization, id=request.id))

        assert Notification.objects(user=applicant).count() == 1
        assert Notification.objects(user=follower).count() == 0
        assert mailed(mails, follower) == []

    def test_ignoring_an_organization_covers_its_badges(self):
        admin = UserFactory()
        organization = OrganizationFactory(admins=[admin])
        ignore(admin, organization)

        organization.add_badge(CERTIFIED)

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

    def test_ignoring_a_dataset_covers_its_reuses_and_dataservices(self):
        owner = UserFactory()
        dataset = DatasetFactory(owner=owner)
        ignore(owner, dataset)

        ReuseFactory(datasets=[dataset])
        DataserviceFactory(datasets=[dataset])

        assert Notification.objects(user=owner).count() == 0

    def test_reuses_and_dataservices_can_be_decided_apart(self):
        owner = UserFactory()
        dataset = DatasetFactory(owner=owner)
        ignore(owner, dataset, NotificationType.REUSE_CREATED)

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
        follow(admin, dataset, NotificationType.DISCUSSION_COMMENT)

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
        follow(admin, dataset, NotificationType.DISCUSSION_COMMENT)

        comment(discussion)

        assert Notification.objects(user=admin).count() == 0

    def test_a_subject_can_be_followed_for_its_new_discussions_only(self):
        outsider = UserFactory()
        dataset = DatasetFactory(organization=OrganizationFactory())
        follow(outsider, dataset, NotificationType.DISCUSSION_NEW)

        comment(open_discussion(dataset))

        assert [notification.type for notification in Notification.objects(user=outsider)] == [
            NotificationType.DISCUSSION_NEW
        ]

    def test_a_type_can_be_turned_off_everywhere(self):
        owner = UserFactory()
        dataset = DatasetFactory(owner=owner)
        decide(owner, event=NotificationType.REUSE_CREATED, enabled=False)

        ReuseFactory(datasets=[dataset])
        DataserviceFactory(datasets=[dataset])

        assert [notification.type for notification in Notification.objects(user=owner)] == [
            NotificationType.DATASERVICE_CREATED
        ]


class OrganizationSettingsTest(APITestCase):
    """What a rule on an organization does: everything about it, or only what one
    follows."""

    def test_an_editor_can_hear_about_everything_of_one_organization(self):
        editor = UserFactory()
        critical, other = (
            OrganizationFactory(editors=[editor]),
            OrganizationFactory(editors=[editor]),
        )
        follow(editor, critical)

        open_discussion(DatasetFactory(organization=critical))
        open_discussion(DatasetFactory(organization=other))

        [notification] = Notification.objects(user=editor)
        assert notification.details.discussion.subject.organization == critical

    def test_an_administrator_can_hear_only_what_they_follow_in_one_organization(self):
        admin = UserFactory()
        organization = OrganizationFactory(admins=[admin])
        followed = DatasetFactory(organization=organization)
        ignore(admin, organization)
        follow(admin, followed)

        open_discussion(followed)
        open_discussion(DatasetFactory(organization=organization))

        [notification] = Notification.objects(user=admin)
        assert notification.details.discussion.subject == followed

    def test_a_partial_editor_can_hear_about_everything_of_their_organization(self):
        """Not only what is assigned to them: their membership lets them read the private
        datasets too."""
        lea = UserFactory()
        organization = OrganizationFactory(partial_editors=[lea])
        follow(lea, organization)

        open_discussion(DatasetFactory(organization=organization))
        open_discussion(DatasetFactory(organization=organization, private=True))

        assert Notification.objects(user=lea).count() == 2

    def test_the_threads_one_answered_still_reach_one(self):
        admin = UserFactory()
        organization = OrganizationFactory(admins=[admin])
        ignore(admin, organization)
        discussion = DiscussionFactory(
            subject=DatasetFactory(organization=organization),
            user=UserFactory(),
            discussion=[MessageDiscussionFactory(posted_by=admin)],
        )

        comment(discussion)

        notification = Notification.objects(user=admin).get()
        assert NotificationReason.DISCUSSION_PARTICIPANT in notification.reasons


class DigestTest(PytestOnlyDBTestCase):
    def test_a_digest_recipient_queues_the_mail_instead_of_receiving_it(self):
        admin = UserFactory(mail_cadence=MailCadence.WEEKLY)
        organization = OrganizationFactory(admins=[admin])

        open_discussion(DatasetFactory(organization=organization))

        notification = Notification.objects(user=admin).first()
        assert set(notification.channels) == {APP, MAIL}

    def test_ignoring_an_organization_queues_nothing(self):
        admin = UserFactory(mail_cadence=MailCadence.WEEKLY)
        organization = OrganizationFactory(admins=[admin])
        ignore(admin, organization)

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

    def test_what_was_handled_meanwhile_is_left_out_of_the_digest(self):
        """Answered in the bell on Tuesday, it is no news on Sunday."""
        admin = UserFactory(mail_cadence=MailCadence.WEEKLY)
        open_discussion(DatasetFactory(organization=OrganizationFactory(admins=[admin])))
        age(Notification.objects(user=admin).first(), days=8)
        Notification.objects(user=admin).mark_handled()

        with capture_mails() as mails:
            send_notification_digests()

        assert mails == []

    def test_the_digest_counts_are_in_the_language_of_the_recipient(self):
        """The counts are written while the digest is built, not when it is sent."""
        admin = UserFactory(mail_cadence=MailCadence.WEEKLY, prefered_language="en")
        open_discussion(DatasetFactory(organization=OrganizationFactory(admins=[admin])))
        age(Notification.objects(user=admin).first(), days=8)

        with capture_mails() as mails:
            send_notification_digests()

        [mail] = mailed(mails, admin)
        assert "1 new discussion" in mail.body

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
        assert digest.body.index(older.subject.title) < digest.body.index(newer.subject.title)
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

    def test_a_type_that_never_mails_is_not_queued(self):
        """A reuse creation has no `via_mail`, so going weekly must not conjure a mail
        the immediate path never sends."""
        owner = UserFactory(mail_cadence=MailCadence.WEEKLY)
        dataset = DatasetFactory(owner=owner)

        ReuseFactory(datasets=[dataset])

        notification = Notification.objects(user=owner).first()
        assert notification.channels == [APP]

    @pytest.mark.options(DEFAULT_LANGUAGE="en")
    def test_the_threads_of_one_subject_collapse_into_a_single_line(self):
        """A count of new discussions only means something for what they are about."""
        admin = UserFactory(mail_cadence=MailCadence.WEEKLY)
        organization = OrganizationFactory(admins=[admin])
        dataset = DatasetFactory(organization=organization)
        discussion = open_discussion(dataset)
        open_discussion(dataset)
        for _index in range(3):
            comment(discussion)

        pending = list(Notification.objects(user=admin, channels=MAIL).order_by("created_at"))
        assert len(pending) == 5

        message = notification_digest(pending)
        assert len(message.paragraphs) == 2  # intro, one line
        line = message.paragraphs[1]
        assert str(line) == f"{dataset.title}: 2 new discussions, 3 new comments"
        assert f'href="{dataset.self_web_url(append="/discussions")}"' in line.html

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
    def put_rule(self, enabled, scope=None, event=DISCUSSIONS, **keys):
        return self.put(
            "/api/1/notifications/settings/",
            {"scope": ref(scope) if scope else None, "event": event, "enabled": enabled, **keys},
        )

    def test_deciding_again_replaces_the_previous_answer(self):
        user = self.login()
        dataset = DatasetFactory()

        self.assert201(self.put_rule(True, dataset))
        response = self.put_rule(False, dataset)

        self.assert200(response)
        [listed] = self.get("/api/1/notifications/settings/").json
        assert listed["id"] == response.json["id"]
        assert listed["scope"] == ref(dataset)
        assert listed["event"] == DISCUSSIONS
        assert "channel" not in listed
        assert listed["enabled"] is False
        assert listed["origin"] == FollowOrigin.FOLLOWED
        assert listed["subject"]["title"] == dataset.title
        assert NotificationSetting.objects(user=user).count() == 1

    def test_a_rule_is_written_back_as_it_is_listed(self):
        """The settings screen adds the rule it just wrote to its list as is: an
        organization comes grouped under itself, as on reload."""
        self.login()
        organization = OrganizationFactory()

        response = self.put_rule(False, organization, event=None)

        self.assert201(response)
        assert response.json["subject"]["title"] == organization.name
        assert response.json["subject"]["organization"]["id"] == str(organization.id)

    def test_withdrawing_a_rule_brings_the_reasons_back(self):
        admin = UserFactory()
        dataset = DatasetFactory(organization=OrganizationFactory(admins=[admin]))
        self.login(admin)
        self.assert201(self.put_rule(False, dataset))

        self.assert204(self.put_rule(None, dataset))
        open_discussion(dataset)

        assert NotificationSetting.objects(user=admin).count() == 0
        assert Notification.objects(user=admin).count() == 1

    def test_withdrawing_a_rule_one_never_set_changes_nothing(self):
        self.login()

        self.assert204(self.put_rule(None, DatasetFactory()))

    def test_a_rule_about_everywhere_is_listed_without_a_scope(self):
        """The rules on a kind of notification, read back by the settings screen, have no
        scope at all."""
        user = UserFactory()
        for event in (DISCUSSIONS, NotificationType.REUSE_CREATED):
            decide(user, event=event, enabled=False)
        self.login(user)

        listed = self.get("/api/1/notifications/settings/").json

        assert sorted((rule["scope"], rule["event"]) for rule in listed) == [
            (None, DISCUSSIONS),
            (None, NotificationType.REUSE_CREATED),
        ]

    def test_nobody_sees_nor_withdraws_the_rules_of_somebody_else(self):
        dataset = DatasetFactory()
        theirs = ignore(UserFactory(), dataset)
        self.login()

        assert self.get("/api/1/notifications/settings/").json == []
        self.assert204(self.put_rule(None, dataset, event=None))
        assert NotificationSetting.objects(id=theirs.id).count() == 1

    def test_a_rule_cannot_be_scoped_to_a_user(self):
        self.login()

        response = self.put_rule(True, UserFactory())

        self.assert400(response)
        assert NotificationSetting.objects.count() == 0

    def test_a_rule_names_a_type_or_a_prefix_of_one(self):
        self.login()
        dataset = DatasetFactory()

        for event in ("NewDiscussion", "Unknown", "discuss"):
            self.assert400(self.put_rule(False, dataset, event=event))

        assert NotificationSetting.objects.count() == 0

    def test_setting_a_follow_by_hand_makes_it_ones_own(self):
        """A follow created by an edit says "because you edited it" until the user
        decides about it themselves."""
        user = self.login()
        dataset = DatasetFactory()
        decide(user, dataset, enabled=True, origin=FollowOrigin.EDITED)

        response = self.put_rule(True, dataset, event=None)

        self.assert200(response)
        assert NotificationSetting.objects(user=user).get().origin == FollowOrigin.FOLLOWED

    def test_a_rule_goes_with_its_subject(self):
        user = self.login()
        discussion = DiscussionFactory(subject=DatasetFactory())
        ignore(user, discussion)

        discussion.delete()

        response = self.get("/api/1/notifications/settings/")
        self.assert200(response)
        assert response.json == []

    def test_a_rule_goes_with_a_subject_purged_in_bulk(self):
        user = self.login()
        dataset = DatasetFactory()
        discussion = DiscussionFactory(subject=dataset)
        ignore(user, discussion)

        Discussion.objects(subject=dataset).delete()

        assert NotificationSetting.objects(user=user).count() == 0

    def test_settings_require_an_account(self):
        self.assert401(self.get("/api/1/notifications/settings/"))
        self.assert401(self.put_rule(True, DatasetFactory()))


class NotificationResolvedAPITest(APITestCase):
    def resolved(self, scopes=(), events=()):
        query = [
            *(("scope", f"{scope.__class__.__name__}:{scope.id}") for scope in scopes),
            *(("event", event) for event in events),
        ]
        return self.get("/api/1/notifications/resolved/", query_string=query)

    def test_nothing_reaches_a_user_who_paused_everything(self):
        admin = UserFactory(notifications_paused=True)
        organization = OrganizationFactory(admins=[admin])
        self.login(admin)

        [answer] = self.resolved(scopes=[organization], events=[DISCUSSIONS]).json

        assert answer["reasons"] == [NotificationReason.ORGANIZATION_ADMIN]
        assert answer["channels"] == []

    def test_an_administrator_hears_about_their_organization(self):
        admin = self.login()
        organization = OrganizationFactory(admins=[admin])

        [answer] = self.resolved(scopes=[organization], events=[DISCUSSIONS]).json

        assert answer["scope"] == ref(organization)
        assert answer["reasons"] == [NotificationReason.ORGANIZATION_ADMIN]
        assert answer["channels"] == [APP, MAIL]

    def test_an_owner_hears_about_the_threads_of_their_dataset(self):
        owner = self.login()
        discussion = DiscussionFactory(subject=DatasetFactory(owner=owner))

        [answer] = self.resolved(scopes=[discussion], events=[DISCUSSIONS]).json

        assert answer["reasons"] == [NotificationReason.OWNER]
        assert answer["channels"] == [APP, MAIL]

    def test_a_follow_gives_its_reason(self):
        user = self.login()
        followed, edited = DatasetFactory(), DatasetFactory()
        follow(user, followed)
        decide(user, edited, enabled=True, origin=FollowOrigin.EDITED)

        answers = self.resolved(scopes=[followed, edited], events=[DISCUSSIONS]).json

        assert [answer["reasons"] for answer in answers] == [
            [NotificationReason.EXPLICIT_SUBSCRIBER],
            [NotificationReason.CONTRIBUTOR],
        ]

    def test_nothing_concerns_an_outsider(self):
        self.login()

        [answer] = self.resolved(scopes=[DatasetFactory()], events=[DISCUSSIONS]).json

        assert answer == {
            "scope": answer["scope"],
            "event": DISCUSSIONS,
            "channels": [],
            "reasons": [],
        }

    def test_an_ignored_thread_resolves_to_nothing(self):
        owner = self.login()
        discussion = DiscussionFactory(subject=DatasetFactory(owner=owner))
        ignore(owner, discussion, DISCUSSIONS)

        [answer] = self.resolved(scopes=[discussion], events=[DISCUSSIONS]).json

        assert answer["channels"] == []

    def test_one_answer_per_combination_of_repeated_keys(self):
        """A page asks once for all of its threads."""
        owner = self.login()
        dataset = DatasetFactory(owner=owner)
        threads = [DiscussionFactory(subject=dataset) for _ in range(3)]
        ignore(owner, threads[1])

        answers = self.resolved(
            scopes=threads, events=[NotificationType.DISCUSSION_NEW, DISCUSSIONS]
        ).json

        assert [(answer["scope"]["id"], answer["event"]) for answer in answers] == [
            (str(thread.id), event)
            for thread in threads
            for event in (NotificationType.DISCUSSION_NEW, DISCUSSIONS)
        ]
        assert [bool(answer["channels"]) for answer in answers] == [
            True,
            True,
            False,
            False,
            True,
            True,
        ]

    def test_unknown_keys_are_refused(self):
        self.login()

        self.assert400(self.get("/api/1/notifications/resolved/?event=Unknown"))
        self.assert400(self.get("/api/1/notifications/resolved/?scope=User:anything"))
        self.assert400(
            self.get("/api/1/notifications/resolved/?scope=Dataset:000000000000000000000000")
        )

    def test_resolving_requires_an_account(self):
        self.assert401(self.get("/api/1/notifications/resolved/"))


class MeMailSettingsAPITest(APITestCase):
    def test_the_mail_cadence_is_set_on_me_and_defers_the_mails(self):
        admin = UserFactory()
        organization = OrganizationFactory(admins=[admin])
        dataset = DatasetFactory(organization=organization)
        self.login(admin)

        response = self.put("/api/1/me/", {"mail_cadence": MailCadence.WEEKLY})
        self.assert200(response)
        assert response.json["mail_cadence"] == MailCadence.WEEKLY

        with capture_mails() as mails:
            open_discussion(dataset)

        assert mailed(mails, admin) == []

    def test_the_mail_settings_of_somebody_else_are_not_disclosed(self):
        other = UserFactory(mail_cadence=MailCadence.WEEKLY, notifications_paused=True)
        self.login()

        response = self.get(f"/api/1/users/{other.id}/")

        self.assert200(response)
        assert response.json["mail_cadence"] is None
        assert response.json["notifications_paused"] is None

    def test_notifications_are_paused_and_resumed_on_me(self):
        admin = UserFactory()
        organization = OrganizationFactory(admins=[admin])
        self.login(admin)

        response = self.put("/api/1/me/", {"notifications_paused": True})
        open_discussion(DatasetFactory(organization=organization))

        self.assert200(response)
        assert response.json["notifications_paused"] is True
        assert Notification.objects(user=admin).count() == 0

        self.put("/api/1/me/", {"notifications_paused": False})
        open_discussion(DatasetFactory(organization=organization))

        assert Notification.objects(user=admin).count() == 1


class NotificationReasonsAPITest(APITestCase):
    def test_the_bell_tells_why_the_user_is_concerned(self):
        admin = UserFactory()
        organization = OrganizationFactory(admins=[admin])
        open_discussion(DatasetFactory(organization=organization))
        self.login(admin)

        response = self.get("/api/1/notifications/")

        self.assert200(response)
        assert [n["reasons"] for n in response.json["data"]] == [
            [NotificationReason.ORGANIZATION_ADMIN]
        ]

    def test_the_bell_tells_which_notifications_ask_for_an_action(self):
        recipient = self.login()
        owner = UserFactory()
        TransferFactory(
            user=owner,
            owner=owner,
            recipient=recipient,
            subject=DatasetFactory(owner=owner),
            status="pending",
        )
        open_discussion(DatasetFactory(owner=recipient))

        response = self.get("/api/1/notifications/")

        assert sorted((n["type"], n["requires_action"]) for n in response.json["data"]) == [
            (NotificationType.DISCUSSION_NEW, False),
            (NotificationType.TRANSFER_REQUESTED, True),
        ]


class FollowWhatOneWorksOnTest(APITestCase):
    def edit(self, dataset):
        data = dataset.to_dict()
        data["description"] = "new description"
        return self.put(url_for("api.dataset", dataset=dataset), data)

    def test_an_editor_who_edits_a_dataset_follows_it(self):
        """Sofia no longer has to follow by hand what she works on."""
        sofia = UserFactory()
        dataset = DatasetFactory(organization=OrganizationFactory(editors=[sofia]))
        self.login(sofia)

        response = self.edit(dataset)
        open_discussion(dataset)

        self.assert200(response)
        setting = NotificationSetting.objects(user=sofia).get()
        assert (setting.scope, setting.enabled, setting.origin) == (
            dataset,
            True,
            FollowOrigin.EDITED,
        )
        notification = Notification.objects(user=sofia).get()
        assert NotificationReason.CONTRIBUTOR in notification.reasons

    def test_editing_what_one_follows_changes_nothing(self):
        """Already followed by hand: it stays a follow of one's own."""
        sofia = UserFactory()
        dataset = DatasetFactory(organization=OrganizationFactory(editors=[sofia]))
        follow(sofia, dataset)
        self.login(sofia)

        self.assert200(self.edit(dataset))

        setting = NotificationSetting.objects(user=sofia).get()
        assert setting.origin == FollowOrigin.FOLLOWED

    def test_an_editor_who_edits_a_reuse_follows_it(self):
        editor = UserFactory()
        reuse = ReuseFactory(organization=OrganizationFactory(editors=[editor]))
        self.login(editor)
        data = reuse.to_dict()
        data["description"] = "new description"

        self.assert200(self.put(url_for("api.reuse", reuse=reuse), data))

        assert NotificationSetting.objects(user=editor, scope=reuse, enabled=True).count() == 1

    def test_an_editor_who_adds_a_resource_follows_the_dataset(self):
        """The most common edit of a dataset, saved without going through the dataset."""
        editor = UserFactory()
        dataset = DatasetFactory(organization=OrganizationFactory(editors=[editor]))
        self.login(editor)

        response = self.post(
            url_for("api.resources", dataset=dataset),
            ResourceFactory.as_dict() | {"filetype": "remote"},
        )

        self.assert201(response)
        assert NotificationSetting.objects(user=editor, scope=dataset, enabled=True).count() == 1

    def test_an_editor_who_edits_a_dataservice_follows_it(self):
        editor = UserFactory()
        dataservice = DataserviceFactory(organization=OrganizationFactory(editors=[editor]))
        self.login(editor)

        response = self.patch(
            url_for("api.dataservice", dataservice=dataservice), {"title": "new title"}
        )

        self.assert200(response)
        assert (
            NotificationSetting.objects(user=editor, scope=dataservice, enabled=True).count() == 1
        )

    def test_an_editor_who_creates_a_dataset_follows_it(self):
        editor = UserFactory()
        organization = OrganizationFactory(editors=[editor])
        self.login(editor)

        response = self.post(
            url_for("api.datasets"),
            DatasetFactory.as_dict() | {"organization": str(organization.id)},
        )

        self.assert201(response)
        setting = NotificationSetting.objects(user=editor, enabled=True).get()
        assert str(setting.scope.id) == response.json["id"]

    def test_an_administrator_follows_too_so_as_to_keep_it_as_an_editor(self):
        admin = UserFactory()
        organization = OrganizationFactory(admins=[admin])
        dataset = DatasetFactory(organization=organization)
        self.login(admin)

        self.assert200(self.edit(dataset))
        organization.members[0].role = "editor"
        organization.save()
        open_discussion(dataset)

        assert Notification.objects(user=admin).count() == 1

    def test_editing_what_one_ignores_keeps_it_ignored(self):
        editor = UserFactory()
        dataset = DatasetFactory(organization=OrganizationFactory(editors=[editor]))
        ignore(editor, dataset)
        self.login(editor)

        self.assert200(self.edit(dataset))

        assert [setting.enabled for setting in NotificationSetting.objects(user=editor)] == [False]

    def test_editing_outside_of_ones_organizations_follows_nothing(self):
        """A site administrator fixing somebody else's dataset has not worked on it."""
        self.login(AdminFactory())
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
        editor = UserFactory()
        organization = OrganizationFactory(editors=[editor])
        dataset = DatasetFactory(organization=organization)
        follow(editor, dataset)
        self.login(editor)

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
