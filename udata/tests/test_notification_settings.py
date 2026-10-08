from datetime import UTC, datetime, timedelta
from smtplib import SMTPRecipientsRefused
from types import SimpleNamespace

import pytest
from bson import ObjectId
from flask import url_for
from mongoengine import NotUniqueError, ValidationError
from mongoengine.connection import get_db

import udata
import udata.features.notifications.follow
import udata.models  # noqa: F401 -- registers every document before the imports below
from udata.api.oauth2 import OAuth2Client, OAuth2Token
from udata.core.dataservices.activities import UserUpdatedDataservice
from udata.core.dataservices.factories import DataserviceFactory
from udata.core.dataset.activities import UserUpdatedDataset
from udata.core.dataset.factories import DatasetFactory, ResourceFactory
from udata.core.discussions.factories import DiscussionFactory, MessageDiscussionFactory
from udata.core.discussions.models import Discussion
from udata.core.discussions.notifications import DiscussionNotificationDetails
from udata.core.organization.assignment import Assignment
from udata.core.organization.constants import CERTIFIED, ORG_ROLES
from udata.core.organization.factories import OrganizationFactory
from udata.core.organization.models import MembershipRequest
from udata.core.post.factories import PostFactory
from udata.core.reuse.activities import UserUpdatedReuse
from udata.core.reuse.factories import ReuseFactory
from udata.core.user.factories import AdminFactory, UserFactory
from udata.db.migrations import load_migration
from udata.features.notifications.api import MAX_RESOLVED_SUBJECTS
from udata.features.notifications.constants import (
    REASON_BY_ORGANIZATION_ROLE,
    TYPES_REQUIRING_ACTION,
    FollowOrigin,
    MailCadence,
    NotificationReason,
    NotificationType,
    event_chain,
    is_event_name,
)
from udata.features.notifications.events import event_for_type
from udata.features.notifications.mails import notification_digest, reason_sentence
from udata.features.notifications.models import SCOPE_MODELS, Notification
from udata.features.notifications.settings import (
    HEARD_BY_EDITORS,
    NOTIFICATION_SCOPES,
    NotificationSetting,
    Rule,
    resolve,
    rules_for,
)
from udata.features.notifications.tasks import send_notification_digests
from udata.features.transfer.factories import TransferFactory
from udata.mail import MailMessage
from udata.tests.api import APITestCase, PytestOnlyDBTestCase
from udata.tests.helpers import capture_mails

DISCUSSIONS = "discussion"


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
        assert Notification.objects(user=naima).count() == 2

        for notification in Notification.objects(user=naima):
            age(notification, days=8)

        with capture_mails() as weekly:
            send_notification_digests()

        assert len(mailed(weekly, naima)) == 1
        # Still readable in the bell afterwards: the digest only empties the mail queue.
        assert Notification.objects(user=naima).count() == 2
        assert Notification.objects(user=naima, mail_pending=True).count() == 0

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

    def test_a_partial_editor_hears_who_reuses_their_datasets_and_an_editor_does_not(self):
        """A reuse or an API built on an assigned dataset is part of looking after it. An
        editor, who never touched the dataset, keeps out of it."""
        lea = UserFactory()
        editor = UserFactory()
        organization = OrganizationFactory(partial_editors=[lea], editors=[editor])
        assigned = DatasetFactory(organization=organization)
        Assignment.objects.create(user=lea, organization=organization, subject=assigned)

        ReuseFactory(datasets=[assigned])
        DataserviceFactory(datasets=[assigned])

        assert sorted(notification.type for notification in Notification.objects(user=lea)) == [
            NotificationType.DATASERVICE_CREATED,
            NotificationType.REUSE_CREATED,
        ]
        assert Notification.objects(user=editor).count() == 0

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

    def test_every_type_one_can_turn_off_is_named(self):
        """The ways out of a mail name the type they stop."""
        for notification_type in set(NotificationType) - TYPES_REQUIRING_ACTION:
            assert event_for_type(notification_type).label is not None, notification_type

    def test_every_organization_role_maps_to_a_reason(self):
        assert set(REASON_BY_ORGANIZATION_ROLE) == set(ORG_ROLES)

    def test_every_reason_is_explained_in_a_mail(self):
        """A reason with no sentence leaves the footer without its explanation."""
        dataset = SimpleNamespace(organization=SimpleNamespace(name="Org"))
        for reason in NotificationReason:
            assert reason_sentence(reason, dataset) is not None, reason

    def test_what_editors_hear_by_default_is_a_real_event(self):
        assert is_event_name(HEARD_BY_EDITORS)

    def test_every_scope_takes_its_rules_along_when_deleted(self):
        """A scope missing from the cleanup leaves rules no one can list nor withdraw."""
        assert {model.__name__ for model in SCOPE_MODELS} == set(NOTIFICATION_SCOPES)


class EventNameTest:
    def test_a_type_and_its_prefixes_are_event_names(self):
        assert is_event_name(NotificationType.DISCUSSION_COMMENT)
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
NEW = event_chain(NotificationType.DISCUSSION_NEW)
COMMENT = event_chain(NotificationType.DISCUSSION_COMMENT)
BADGE = event_chain(NotificationType.ORGANIZATION_BADGE_CERTIFIED)


def rule(scope=None, event=None, enabled=True, origin=FollowOrigin.FOLLOWED):
    return Rule(enabled=enabled, scope=scope.id if scope else None, event=event, origin=origin)


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
            [], BADGE,
            [ORGANIZATION], {NotificationReason.ORGANIZATION_EDITOR},
        ) is True  # fmt: skip

    def test_following_a_dataset_beats_the_default_of_editors(self):
        rules = [rule(scope=DATASET)]

        assert resolve(rules, NEW, SCOPES, {NotificationReason.ORGANIZATION_EDITOR}) is True

    def test_an_event_on_a_thread_beats_the_thread(self):
        rules = [
            rule(scope=THREAD, enabled=False),
            rule(scope=THREAD, event=NotificationType.DISCUSSION_COMMENT),
        ]

        assert resolve(rules, COMMENT, SCOPES, {NotificationReason.ORGANIZATION_ADMIN}) is True

    def test_the_most_generous_reason_wins(self):
        """Silenced as an editor by default, heard as a participant of the thread."""
        reasons = {
            NotificationReason.ORGANIZATION_EDITOR,
            NotificationReason.DISCUSSION_PARTICIPANT,
        }

        assert resolve([], COMMENT, SCOPES, reasons) is True

    def test_a_choice_on_an_event_beats_the_default_of_a_reason(self):
        rules = [rule(event=NotificationType.DISCUSSION_NEW)]

        assert resolve(rules, NEW, SCOPES, {NotificationReason.ORGANIZATION_EDITOR}) is True

    def test_ignoring_a_dataset(self):
        rules = [rule(scope=DATASET, enabled=False)]

        assert resolve(rules, NEW, SCOPES, {NotificationReason.ORGANIZATION_ADMIN}) is False

    def test_the_users_broad_choice_beats_a_precise_default(self):
        """Defaults are only read where the user said nothing: "editors, yes" set by the
        user is not undone by the narrower default of the badges."""
        rules = [rule(enabled=False)]

        assert resolve(
            rules, BADGE,
            [ORGANIZATION], {NotificationReason.ORGANIZATION_EDITOR},
        ) is False  # fmt: skip

    def test_rules_about_other_subjects_or_events_are_ignored(self):
        rules = [
            rule(scope=SimpleNamespace(id="elsewhere"), enabled=False),
            rule(event=NotificationType.REUSE_CREATED, enabled=False),
        ]

        assert resolve(rules, NEW, SCOPES, {NotificationReason.ORGANIZATION_ADMIN}) is True

    def test_muting_an_organization_holds_against_what_one_edited_in_it(self):
        """A follow made by udata itself was never chosen: a broader "no" beats it."""
        rules = [
            rule(scope=DATASET, origin=FollowOrigin.EDITED),
            rule(scope=ORGANIZATION, enabled=False),
        ]

        assert resolve(rules, NEW, SCOPES, {NotificationReason.CONTRIBUTOR}) is False

    def test_a_follow_set_by_hand_still_beats_a_broader_no(self):
        rules = [rule(scope=DATASET), rule(scope=ORGANIZATION, enabled=False)]

        assert resolve(rules, NEW, SCOPES, {NotificationReason.EXPLICIT_SUBSCRIBER}) is True

    def test_turning_a_type_off_holds_against_a_followed_subject(self):
        """Each rule is the more specific on one dimension: the "no" wins."""
        rules = [rule(scope=DATASET), rule(event=NotificationType.DISCUSSION_NEW, enabled=False)]

        assert resolve(rules, NEW, SCOPES, {NotificationReason.CONTRIBUTOR}) is False

    def test_a_rule_more_specific_on_both_dimensions_still_wins(self):
        rules = [
            rule(event="discussion", enabled=False),
            rule(scope=DATASET, event=NotificationType.DISCUSSION_NEW),
        ]

        assert resolve(rules, NEW, SCOPES, {NotificationReason.ORGANIZATION_ADMIN}) is True

    def test_ignoring_what_a_thread_is_about_silences_its_participant(self):
        rules = [rule(scope=DATASET, enabled=False)]

        assert resolve(rules, COMMENT, SCOPES, {NotificationReason.DISCUSSION_PARTICIPANT}) is False

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
        assert notification.mail_pending is False

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
        assert f"Stop receiving: New discussions: {settings}?event=discussion.new" in mail.body

    def test_what_no_digest_summarizes_is_mailed_at_once(self):
        """A badge has no line in a digest: a weekly recipient still gets its mail."""
        admin = UserFactory(mail_cadence=MailCadence.WEEKLY)
        organization = OrganizationFactory(admins=[admin])

        with capture_mails() as mails:
            organization.add_badge(CERTIFIED)

        assert len(mailed(mails, admin)) == 1
        assert Notification.objects(user=admin).first().mail_pending is False

    @pytest.mark.options(CDATA_BASE_URL="https://www.data.gouv.fr", DEFAULT_LANGUAGE="en")
    def test_a_badge_mail_offers_its_organization_and_all_badges(self):
        """It says "Badges of the organization": the next badge, of another kind, has to
        stay out too."""
        admin = UserFactory()
        organization = OrganizationFactory(admins=[admin])

        with capture_mails() as mails:
            organization.add_badge(CERTIFIED)

        [mail] = mailed(mails, admin)
        assert f"scope=Organization%3A{organization.id}" in mail.body
        assert "event=organization.badge\n" in mail.body
        assert "Stop following this discussion" not in mail.body

    @pytest.mark.options(DEFAULT_LANGUAGE="en")
    def test_a_badge_tells_a_partial_editor_why_without_assigning_them_the_organization(self):
        """A badge is about the organization as a whole: nothing of it was assigned."""
        lea = UserFactory()
        organization = OrganizationFactory(partial_editors=[lea])

        with capture_mails() as mails:
            organization.add_badge(CERTIFIED)

        [mail] = mailed(mails, lea)
        assert f"you are a partial editor of {organization.name}" in mail.body
        assert "is assigned to you" not in mail.body

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

    def test_a_deleted_account_hears_nothing_of_what_it_followed(self):
        follower = UserFactory()
        dataset = DatasetFactory(organization=OrganizationFactory())
        follow(follower, dataset)
        follower.mark_as_deleted(notify=False)

        with capture_mails() as mails:
            open_discussion(dataset)

        assert Notification.objects(user=follower).count() == 0
        assert mailed(mails, follower) == []

    def test_a_deleted_account_hears_nothing_of_what_it_still_owns(self):
        owner = UserFactory()
        dataset = DatasetFactory(owner=owner)
        owner.mark_as_deleted(notify=False)

        with capture_mails() as mails:
            open_discussion(dataset)

        assert Notification.objects(user=owner).count() == 0
        assert mailed(mails, owner) == []

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

    def test_a_type_turned_off_stays_off_on_what_one_edited(self):
        """Editing follows the dataset; "no new reuses" set from the bell still holds."""
        editor = UserFactory()
        dataset = DatasetFactory(organization=OrganizationFactory(editors=[editor]))
        decide(editor, dataset, enabled=True, origin=FollowOrigin.EDITED)
        decide(editor, event=NotificationType.REUSE_CREATED, enabled=False)

        ReuseFactory(datasets=[dataset])
        DataserviceFactory(datasets=[dataset])

        assert [notification.type for notification in Notification.objects(user=editor)] == [
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
        assert notification.mail_pending is True

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

        assert Notification.objects(user=admin).first().mail_pending is False

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
        assert notification.mail_pending is False

    def test_switching_back_to_immediate_releases_the_queue(self):
        admin = UserFactory(mail_cadence=MailCadence.WEEKLY)
        organization = OrganizationFactory(admins=[admin])
        open_discussion(DatasetFactory(organization=organization))
        admin.mail_cadence = MailCadence.IMMEDIATE
        admin.save()

        with capture_mails() as mails:
            send_notification_digests()

        assert [mail.recipients for mail in mails] == [[admin.email]]
        assert Notification.objects(user=admin, mail_pending=True).count() == 0

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
        assert Notification.objects(user=admin, mail_pending=True).count() == 0

    def test_one_failing_digest_does_not_deprive_the_others(self, caplog, monkeypatch):
        # Two broken users, whatever order the job meets them in: the second one is only
        # reached if the job carries on after the first failure.
        broken = [UserFactory(mail_cadence=MailCadence.WEEKLY) for _ in range(2)]
        healthy = UserFactory(mail_cadence=MailCadence.WEEKLY)
        for user in [*broken, healthy]:
            open_discussion(DatasetFactory(organization=OrganizationFactory(admins=[user])))
        for notification in Notification.objects:
            age(notification, days=8)
        send = MailMessage.send

        def refused_for_the_broken(message, recipient):
            if recipient in broken:
                raise SMTPRecipientsRefused({recipient.email: (550, b"Mailbox unavailable")})
            send(message, recipient)

        monkeypatch.setattr(MailMessage, "send", refused_for_the_broken)

        with capture_mails() as mails:
            send_notification_digests()

        assert [mail.recipients for mail in mails] == [[healthy.email]]
        assert Notification.objects(user=healthy, mail_pending=True).count() == 0
        for user in broken:
            assert Notification.objects(user=user, mail_pending=True).count() == 1
        # The trace has to reach the logs and Sentry, not only the exception message.
        failures = [record for record in caplog.records if record.levelname == "ERROR"]
        assert [failure.exc_info[0] for failure in failures] == [
            SMTPRecipientsRefused,
            SMTPRecipientsRefused,
        ]

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

    def test_a_subject_gone_does_not_hold_back_the_rest_of_the_digest(self):
        """Deleting a post leaves its discussions, and their notifications, behind."""
        admin = UserFactory(mail_cadence=MailCadence.WEEKLY)
        dataset = DatasetFactory(organization=OrganizationFactory(admins=[admin]))
        post = PostFactory()
        orphan = DiscussionFactory(subject=post)
        Notification(
            user=admin,
            type=NotificationType.DISCUSSION_NEW,
            details=DiscussionNotificationDetails(discussion=orphan),
            mail_pending=True,
        ).save()
        open_discussion(dataset)
        post.delete()
        for notification in Notification.objects(user=admin):
            age(notification, days=8)

        with capture_mails() as mails:
            send_notification_digests()

        [mail] = mailed(mails, admin)
        assert dataset.title in mail.body
        assert Notification.objects(user=admin, mail_pending=True).count() == 0

    def test_pausing_holds_back_what_was_already_queued(self):
        admin = UserFactory(mail_cadence=MailCadence.WEEKLY)
        open_discussion(DatasetFactory(organization=OrganizationFactory(admins=[admin])))
        age(Notification.objects(user=admin).first(), days=8)
        turn_everything_off(admin)

        with capture_mails() as mails:
            send_notification_digests()

        assert mails == []

    def test_resuming_does_not_release_what_was_queued_before_the_pause(self):
        admin = UserFactory(mail_cadence=MailCadence.WEEKLY)
        open_discussion(DatasetFactory(organization=OrganizationFactory(admins=[admin])))
        age(Notification.objects(user=admin).first(), days=8)
        turn_everything_off(admin)

        with capture_mails() as mails:
            send_notification_digests()
            admin.notifications_paused = False
            admin.save()
            send_notification_digests()

        assert mails == []
        assert Notification.objects(user=admin).first().mail_pending is False

    def test_a_type_that_never_mails_is_not_queued(self):
        """A reuse creation has no `via_mail`, so going weekly must not conjure a mail
        the immediate path never sends."""
        owner = UserFactory(mail_cadence=MailCadence.WEEKLY)
        dataset = DatasetFactory(owner=owner)

        ReuseFactory(datasets=[dataset])

        notification = Notification.objects(user=owner).first()
        assert notification.mail_pending is False

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

        pending = list(Notification.objects(user=admin, mail_pending=True).order_by("created_at"))
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

    def test_a_rule_without_enabled_is_refused_rather_than_withdrawn(self):
        user = self.login()
        dataset = DatasetFactory()
        ignore(user, dataset)

        response = self.put(
            "/api/1/notifications/settings/", {"scope": ref(dataset), "event": None}
        )

        self.assert400(response)
        assert NotificationSetting.objects(user=user).count() == 1

    def test_deciding_again_replaces_the_previous_answer(self):
        user = self.login()
        dataset = DatasetFactory()

        self.assert201(self.put_rule(True, dataset))
        response = self.put_rule(False, dataset)

        self.assert200(response)
        [listed] = self.get("/api/1/notifications/settings/").json["data"]
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
        organization belongs to no other one, as on reload."""
        self.login()
        organization = OrganizationFactory()

        response = self.put_rule(False, organization, event=None)

        self.assert201(response)
        assert response.json["subject"]["title"] == organization.name
        assert response.json["subject"]["organization"] is None

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

        listed = self.get("/api/1/notifications/settings/").json["data"]

        assert sorted((rule["scope"], rule["event"]) for rule in listed) == [
            (None, DISCUSSIONS),
            (None, NotificationType.REUSE_CREATED),
        ]

    def test_withdrawing_an_automatic_follow_turns_it_into_a_no(self):
        """Withdrawn, the next edit would make it again, whichever client withdrew it."""
        user = self.login()
        dataset = DatasetFactory()
        decide(user, dataset, enabled=True, origin=FollowOrigin.EDITED)

        response = self.put_rule(None, dataset, event=None)

        self.assert200(response)
        assert response.json["enabled"] is False
        setting = NotificationSetting.objects(user=user).get()
        assert (setting.enabled, setting.origin) == (False, FollowOrigin.FOLLOWED)

    def test_the_rules_are_listed_by_page_latest_first(self):
        user = self.login()
        older, newer = DatasetFactory(), DatasetFactory()
        follow(user, older)
        follow(user, newer)

        first = self.get("/api/1/notifications/settings/?page_size=1").json
        second = self.get("/api/1/notifications/settings/?page_size=1&page=2").json

        assert first["total"] == 2
        assert [rule["scope"] for rule in first["data"] + second["data"]] == [
            ref(newer),
            ref(older),
        ]

    def test_the_follows_and_the_other_rules_are_listed_apart(self):
        """The settings screen pages through each of its two lists on its own."""
        user = self.login()
        followed, ignored = DatasetFactory(), DatasetFactory()
        follow(user, followed)
        ignore(user, ignored)
        decide(user, event=NotificationType.REUSE_CREATED, enabled=False)

        follows = self.get("/api/1/notifications/settings/?followed=true").json["data"]
        others = self.get("/api/1/notifications/settings/?followed=false").json["data"]

        assert [rule["scope"] for rule in follows] == [ref(followed)]
        assert [(rule["scope"], rule["event"]) for rule in others] == [
            (None, NotificationType.REUSE_CREATED),
            (ref(ignored), None),
        ]

    def test_nobody_sees_nor_withdraws_the_rules_of_somebody_else(self):
        dataset = DatasetFactory()
        theirs = ignore(UserFactory(), dataset)
        self.login()

        assert self.get("/api/1/notifications/settings/").json["data"] == []
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
        assert response.json["data"] == []

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
    def resolved(self, scopes, event=None):
        query = [("scope", f"{scope.__class__.__name__}:{scope.id}") for scope in scopes]
        if event is not None:
            query.append(("event", event))
        return self.get("/api/1/notifications/resolved/", query_string=query)

    def test_the_subject_is_named_as_the_user_may_see_it(self):
        """What a mail link names is read back from here: a private subject keeps its
        title."""
        self.login()
        organization = OrganizationFactory()
        visible = DatasetFactory(organization=organization)
        private = DatasetFactory(organization=organization, private=True)

        answers = self.resolved([visible, private]).json

        assert answers[0]["subject"] == {
            "title": visible.title,
            "page": visible.self_web_url(),
            "organization": answers[0]["subject"]["organization"],
        }
        assert answers[0]["subject"]["organization"]["id"] == str(organization.id)
        assert answers[1]["subject"] is None

    def test_following_what_one_cannot_read_brings_nothing(self):
        """As at dispatch, which leaves out the followers who may not read the subject."""
        outsider = self.login()
        private = DatasetFactory(organization=OrganizationFactory(), private=True)
        follow(outsider, private)

        [answer] = self.resolved([private], DISCUSSIONS).json

        assert answer["heard"] is False
        assert answer["reasons"] == []

    def test_the_pause_is_left_out_so_that_following_still_shows(self):
        """A follow button keeps telling, and changing, what one follows meanwhile."""
        admin = UserFactory(notifications_paused=True)
        organization = OrganizationFactory(admins=[admin])
        self.login(admin)

        [answer] = self.resolved([organization], DISCUSSIONS).json

        assert answer["reasons"] == [NotificationReason.ORGANIZATION_ADMIN]
        assert answer["heard"] is True

    def test_a_subject_said_no_to_reads_as_muted(self):
        owner = self.login()
        dataset = DatasetFactory(owner=owner)
        ignore(owner, dataset)

        [answer] = self.resolved([dataset]).json

        assert answer["heard"] is False
        assert answer["muted"] is True

    def test_the_events_still_followed_on_a_subject_are_listed(self):
        """Muted as a whole but following its new discussions: asked about everything,
        the subject is not heard, yet some of it is."""
        user = self.login()
        dataset = DatasetFactory()
        ignore(user, dataset)
        follow(user, dataset, NotificationType.DISCUSSION_NEW)
        follow(user, dataset, NotificationType.REUSE_CREATED)

        [everything] = self.resolved([dataset]).json
        [discussions] = self.resolved([dataset], DISCUSSIONS).json

        assert everything["muted"] is True
        assert everything["followed_events"] == [
            NotificationType.DISCUSSION_NEW,
            NotificationType.REUSE_CREATED,
        ]
        assert discussions["followed_events"] == [NotificationType.DISCUSSION_NEW]

    def test_an_administrator_hears_about_their_organization(self):
        admin = self.login()
        organization = OrganizationFactory(admins=[admin])

        [answer] = self.resolved([organization], DISCUSSIONS).json

        assert answer["scope"] == ref(organization)
        assert answer["reasons"] == [NotificationReason.ORGANIZATION_ADMIN]
        assert answer["heard"] is True

    def test_an_owner_hears_about_the_threads_of_their_dataset(self):
        owner = self.login()
        discussion = DiscussionFactory(subject=DatasetFactory(owner=owner))

        [answer] = self.resolved([discussion], DISCUSSIONS).json

        assert answer["reasons"] == [NotificationReason.OWNER]
        assert answer["heard"] is True

    def test_a_follow_gives_its_reason(self):
        user = self.login()
        followed, edited = DatasetFactory(), DatasetFactory()
        follow(user, followed)
        decide(user, edited, enabled=True, origin=FollowOrigin.EDITED)

        answers = self.resolved([followed, edited], DISCUSSIONS).json

        assert [answer["reasons"] for answer in answers] == [
            [NotificationReason.EXPLICIT_SUBSCRIBER],
            [NotificationReason.CONTRIBUTOR],
        ]

    def test_nothing_concerns_an_outsider(self):
        self.login()

        dataset = DatasetFactory()

        [answer] = self.resolved([dataset], DISCUSSIONS).json

        assert answer == {
            "scope": answer["scope"],
            "event": DISCUSSIONS,
            "heard": False,
            "reasons": [],
            "muted": False,
            "followed_events": [],
            "subject": {"title": dataset.title, "page": None, "organization": None},
        }

    def test_an_ignored_thread_resolves_to_nothing(self):
        owner = self.login()
        discussion = DiscussionFactory(subject=DatasetFactory(owner=owner))
        ignore(owner, discussion, DISCUSSIONS)

        [answer] = self.resolved([discussion], DISCUSSIONS).json

        assert answer["heard"] is False

    def test_one_answer_per_subject(self):
        """A page asks once for all of its threads."""
        owner = self.login()
        dataset = DatasetFactory(owner=owner)
        threads = [DiscussionFactory(subject=dataset) for _ in range(3)]
        ignore(owner, threads[1])

        answers = self.resolved(threads, NotificationType.DISCUSSION_NEW).json

        assert [(answer["scope"]["id"], answer["event"]) for answer in answers] == [
            (str(thread.id), NotificationType.DISCUSSION_NEW) for thread in threads
        ]
        assert [answer["heard"] for answer in answers] == [True, False, True]

    def test_a_subject_asked_twice_is_answered_once(self):
        owner = self.login()
        dataset = DatasetFactory(owner=owner)

        answers = self.resolved([dataset, dataset]).json

        assert [answer["scope"] for answer in answers] == [ref(dataset)]

    def test_without_an_event_it_is_about_every_notification(self):
        owner = self.login()
        dataset = DatasetFactory(owner=owner)

        [answer] = self.resolved([dataset]).json

        assert answer["event"] is None
        assert answer["heard"] is True

    def test_unknown_keys_are_refused(self):
        self.login()
        dataset = DatasetFactory()

        self.assert400(self.resolved([dataset], "Unknown"))
        self.assert400(self.get("/api/1/notifications/resolved/?scope=User:anything"))
        self.assert400(
            self.get("/api/1/notifications/resolved/?scope=Dataset:000000000000000000000000")
        )

    def test_a_subject_is_required(self):
        """Without one, nothing reaches anybody: the answer would always be empty."""
        self.login()

        self.assert400(self.get("/api/1/notifications/resolved/?event=discussion"))

    def test_the_number_of_subjects_is_capped(self):
        self.login()
        ids = [f"Dataset:{ObjectId()}" for _ in range(MAX_RESOLVED_SUBJECTS + 1)]

        response = self.get(
            "/api/1/notifications/resolved/", query_string=[("scope", id) for id in ids]
        )

        self.assert400(response)
        assert response.json["message"] == f"At most {MAX_RESOLVED_SUBJECTS} subjects"

    def test_resolving_requires_an_account(self):
        self.assert401(self.get("/api/1/notifications/resolved/"))


class NotificationFollowAPITest(APITestCase):
    def put_follow(self, scope, followed, event=None):
        return self.put(
            "/api/1/notifications/follow/",
            {"scope": ref(scope), "event": event, "followed": followed},
        )

    def rules(self, user):
        return [
            (setting.scope, setting.event, setting.enabled)
            for setting in NotificationSetting.objects(user=user)
        ]

    def test_following_writes_a_follow_and_answers_heard(self):
        user = self.login()
        dataset = DatasetFactory()

        response = self.put_follow(dataset, True, NotificationType.DISCUSSION_NEW)

        self.assert200(response)
        assert response.json["heard"] is True
        assert self.rules(user) == [(dataset, NotificationType.DISCUSSION_NEW, True)]

    def test_stopping_ones_own_follow_only_withdraws_it(self):
        """Nothing else brings these notifications: no "no" is left behind."""
        user = self.login()
        dataset = DatasetFactory()
        follow(user, dataset, NotificationType.DISCUSSION_NEW)

        response = self.put_follow(dataset, False, NotificationType.DISCUSSION_NEW)

        assert response.json["heard"] is False
        assert self.rules(user) == []

    def test_stopping_what_ones_role_brings_says_no(self):
        owner = self.login()
        dataset = DatasetFactory(owner=owner)

        response = self.put_follow(dataset, False)

        assert response.json["heard"] is False
        assert response.json["muted"] is True
        assert self.rules(owner) == [(dataset, None, False)]

    def test_stopping_an_automatic_follow_keeps_it_away(self):
        """Withdrawn, the next edit would make it again."""
        editor = self.login()
        # Created by the editor, so followed by udata itself.
        dataset = DatasetFactory(organization=OrganizationFactory(editors=[editor]))
        assert [setting.origin for setting in NotificationSetting.objects(user=editor)] == [
            FollowOrigin.EDITED
        ]

        self.put_follow(dataset, False)

        [setting] = NotificationSetting.objects(user=editor)
        assert (setting.enabled, setting.origin) == (False, FollowOrigin.FOLLOWED)

    def test_stopping_everything_drops_the_narrower_follows(self):
        user = self.login()
        dataset = DatasetFactory()
        follow(user, dataset, NotificationType.DISCUSSION_NEW)
        follow(user, dataset, NotificationType.REUSE_CREATED)

        response = self.put_follow(dataset, False)

        assert response.json["followed_events"] == []
        assert self.rules(user) == []

    def test_following_everything_drops_a_narrower_no(self):
        """Left behind, "no discussions" would beat the follow the user just asked for."""
        user = self.login()
        dataset = DatasetFactory()
        ignore(user, dataset, DISCUSSIONS)

        response = self.put_follow(dataset, True)

        assert response.json["heard"] is True
        assert self.rules(user) == [(dataset, None, True)]

    def test_stopping_an_organization_stops_the_badges_of_an_editor(self):
        """What the way out of a badge mail does: editors hear about badges alone, and
        asking about every notification must not read as hearing none of them."""
        editor = self.login()
        organization = OrganizationFactory(editors=[editor])

        response = self.put_follow(organization, False)
        organization.add_badge(CERTIFIED)

        assert response.json["heard"] is False
        assert self.rules(editor) == [(organization, None, False)]
        assert Notification.objects(user=editor).count() == 0

    def test_a_partial_editor_does_not_hear_every_discussion_of_their_organization(self):
        """Only those of what was assigned to them, as at dispatch."""
        partial_editor = self.login()
        organization = OrganizationFactory(partial_editors=[partial_editor])

        [answer] = self.get(
            "/api/1/notifications/resolved/",
            query_string={"scope": f"Organization:{organization.id}", "event": DISCUSSIONS},
        ).json

        assert answer["heard"] is False

    def test_a_prefix_only_drops_the_rules_under_it(self):
        """`discussion` covers `discussion.*`, not what merely starts with the same word."""
        user = self.login()
        dataset = DatasetFactory()
        follow(user, dataset, NotificationType.DISCUSSION_NEW)
        ignore(user, dataset, NotificationType.REUSE_CREATED)

        response = self.put_follow(dataset, False, DISCUSSIONS)

        self.assert200(response)
        assert response.json["followed_events"] == []
        assert self.rules(user) == [(dataset, NotificationType.REUSE_CREATED, False)]

    def test_following_a_thread_brings_its_comments(self):
        """From the API to the bell: somebody the thread would never reach."""
        user = self.login()
        discussion = open_discussion(DatasetFactory())

        self.assert200(self.put_follow(discussion, True))
        with capture_mails() as mails:
            comment(discussion)

        [notification] = Notification.objects(user=user)
        assert notification.type == NotificationType.DISCUSSION_COMMENT
        assert notification.details.discussion == discussion
        [mail] = mailed(mails, user)
        assert discussion.title in mail.body

    def test_stopping_what_a_broader_follow_brings_says_no(self):
        user = self.login()
        organization = OrganizationFactory()
        dataset = DatasetFactory(organization=organization)
        follow(user, organization)

        response = self.put_follow(dataset, False)

        assert response.json["heard"] is False
        assert sorted(self.rules(user), key=lambda rule: rule[2]) == [
            (dataset, None, False),
            (organization, None, True),
        ]

    def test_unknown_keys_are_refused(self):
        self.login()
        dataset = DatasetFactory()

        self.assert400(self.put_follow(dataset, True, "Unknown"))
        self.assert400(
            self.put(
                "/api/1/notifications/follow/",
                {"scope": {"class": "Dataset", "id": "not-an-id"}, "followed": True},
            )
        )
        self.assert400(self.put("/api/1/notifications/follow/", {"scope": ref(dataset)}))

    def test_a_body_of_another_shape_is_refused(self):
        self.login()

        self.assert400(self.put("/api/1/notifications/follow/", [{"followed": True}]))
        self.assert400(
            self.put("/api/1/notifications/follow/", {"scope": "Dataset:x", "followed": True})
        )

    def test_following_requires_an_account(self):
        self.assert401(self.put_follow(DatasetFactory(), True))


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

    def test_a_sysadmin_who_edits_follows_nothing(self):
        """Moderating the datasets of an organization one belongs to is not working on
        them for it."""
        sysadmin = AdminFactory()
        dataset = DatasetFactory(organization=OrganizationFactory(editors=[sysadmin]))
        self.login(sysadmin)

        self.assert200(self.edit(dataset))

        assert NotificationSetting.objects.count() == 0

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

    def test_a_script_publishing_with_an_oauth_token_follows_nothing(self):
        editor = UserFactory()
        dataset = DatasetFactory(organization=OrganizationFactory(editors=[editor]))
        client = OAuth2Client.objects.create(
            name="script",
            owner=UserFactory(),
            redirect_uris=["https://script.example.org/callback"],
            secret="s3cr3t",
        )
        token = OAuth2Token.objects.create(
            client=client, user=editor, access_token="access", refresh_token="refresh"
        )
        data = dataset.to_dict()
        data["description"] = "new description"

        response = self.put(
            url_for("api.dataset", dataset=dataset),
            data,
            headers={"Authorization": f"Bearer {token.access_token}"},
        )

        self.assert200(response)
        assert NotificationSetting.objects.count() == 0

    def open_discussion_on(self, dataset):
        return self.post(
            url_for("api.discussions"),
            {"subject": ref(dataset), "title": "A question", "comment": "Is it up to date?"},
        )

    def test_an_editor_who_opens_a_discussion_follows_the_dataset(self):
        """Answering about a dataset is following it: the next questions are for her too."""
        sofia = UserFactory()
        dataset = DatasetFactory(organization=OrganizationFactory(editors=[sofia]))
        self.login(sofia)

        self.assert201(self.open_discussion_on(dataset))
        open_discussion(dataset)

        setting = NotificationSetting.objects(user=sofia).get()
        assert setting.scope == dataset
        assert setting.origin == FollowOrigin.DISCUSSED
        [notification] = Notification.objects(user=sofia)
        assert NotificationReason.DISCUSSANT in notification.reasons

    def test_an_editor_who_answers_a_discussion_follows_the_dataset(self):
        sofia = UserFactory()
        dataset = DatasetFactory(organization=OrganizationFactory(editors=[sofia]))
        discussion = open_discussion(dataset)
        self.login(sofia)

        response = self.post(url_for("api.discussion", id=discussion.id), {"comment": "Yes."})

        self.assert200(response)
        setting = NotificationSetting.objects(user=sofia).get()
        assert setting.scope == dataset
        assert setting.origin == FollowOrigin.DISCUSSED

    def test_answering_outside_of_ones_organizations_follows_nothing(self):
        """A citizen asking a question follows the thread, not the dataset."""
        self.login()
        dataset = DatasetFactory(organization=OrganizationFactory())

        self.assert201(self.open_discussion_on(dataset))

        assert NotificationSetting.objects.count() == 0

    def test_answering_about_what_one_ignores_keeps_it_ignored(self):
        editor = UserFactory()
        dataset = DatasetFactory(organization=OrganizationFactory(editors=[editor]))
        ignore(editor, dataset)
        self.login(editor)

        self.assert201(self.open_discussion_on(dataset))

        assert [setting.enabled for setting in NotificationSetting.objects(user=editor)] == [False]

    def test_answering_with_an_api_key_follows_nothing(self):
        editor = UserFactory()
        dataset = DatasetFactory(organization=OrganizationFactory(editors=[editor]))

        with self.api_user(editor):
            self.assert201(self.open_discussion_on(dataset))

        assert NotificationSetting.objects.count() == 0

    def test_the_followed_subjects_are_listed_with_their_organization(self):
        editor = UserFactory()
        organization = OrganizationFactory(editors=[editor])
        dataset = DatasetFactory(organization=organization)
        follow(editor, dataset)
        self.login(editor)

        [listed] = self.get("/api/1/notifications/settings/").json["data"]

        assert listed["subject"]["title"] == dataset.title
        assert listed["subject"]["organization"]["id"] == str(organization.id)

    def test_a_thread_is_listed_with_its_title_and_the_organization_of_its_subject(self):
        user = self.login()
        organization = OrganizationFactory()
        discussion = DiscussionFactory(subject=DatasetFactory(organization=organization))
        ignore(user, discussion, DISCUSSIONS)

        [listed] = self.get("/api/1/notifications/settings/").json["data"]

        assert listed["subject"]["title"] == discussion.title
        assert listed["subject"]["page"] == discussion.self_web_url()
        assert listed["subject"]["organization"]["id"] == str(organization.id)

    def test_a_subject_out_of_reach_is_listed_without_its_title(self):
        """Left the organization, and the dataset turned private since."""
        user = self.login()
        dataset = DatasetFactory(organization=OrganizationFactory(), private=True)
        follow(user, dataset)

        [listed] = self.get("/api/1/notifications/settings/").json["data"]

        assert listed["subject"] is None


class CreateDiscussionsNotificationsMigrationTest(PytestOnlyDBTestCase):
    def migrate(self):
        load_migration("2026-01-15-create-discussions-notifications.py").migrate(get_db())

    def test_an_unanswered_discussion_notifies_its_recipients_but_its_author(self):
        owner, author = UserFactory(), UserFactory()
        discussion = DiscussionFactory(
            subject=DatasetFactory(owner=owner),
            user=author,
            discussion=[MessageDiscussionFactory(posted_by=author)],
        )

        self.migrate()

        [notification] = Notification.objects
        assert notification.user == owner
        assert notification.type == NotificationType.DISCUSSION_NEW
        assert notification.reasons == [NotificationReason.OWNER]
        assert notification.details.discussion == discussion
        assert notification.details.message_id is None

    def test_an_answered_discussion_notifies_its_last_comment(self):
        owner, author = UserFactory(), UserFactory()
        answer = MessageDiscussionFactory(posted_by=author)
        DiscussionFactory(
            subject=DatasetFactory(owner=owner),
            user=author,
            discussion=[MessageDiscussionFactory(posted_by=author), answer],
        )

        self.migrate()

        [notification] = Notification.objects
        assert notification.user == owner
        assert notification.type == NotificationType.DISCUSSION_COMMENT
        assert notification.details.message_id == answer.id

    def test_a_discussion_already_notified_is_left_alone(self):
        owner = UserFactory()
        open_discussion(DatasetFactory(owner=owner))
        before = [notification.id for notification in Notification.objects]

        self.migrate()

        assert [notification.id for notification in Notification.objects] == before


class FollowWorkedOnSubjectsMigrationTest(PytestOnlyDBTestCase):
    def migrate(self, db):
        load_migration("2026-10-08-follow-worked-on-subjects.py").migrate(db)

    def follows(self):
        return [
            (setting.user, setting.scope, setting.origin) for setting in NotificationSetting.objects
        ]

    def test_the_members_who_edited_follow_what_they_edited(self):
        editor, left = UserFactory(), UserFactory()
        organization = OrganizationFactory(editors=[editor])
        edited, untouched = (
            DatasetFactory(organization=organization),
            DatasetFactory(organization=organization),
        )
        UserUpdatedDataset.objects.create(
            actor=editor, related_to=edited, organization=organization
        )
        UserUpdatedDataset.objects.create(
            actor=left, related_to=untouched, organization=organization
        )

        self.migrate(get_db())

        assert self.follows() == [(editor, edited, FollowOrigin.EDITED)]

    def test_the_members_who_discussed_follow_what_they_discussed(self):
        editor, outsider = UserFactory(), UserFactory()
        dataset = DatasetFactory(organization=OrganizationFactory(editors=[editor]))
        DiscussionFactory(
            subject=dataset,
            user=outsider,
            discussion=[
                MessageDiscussionFactory(posted_by=outsider),
                MessageDiscussionFactory(posted_by=editor),
            ],
        )

        self.migrate(get_db())

        assert self.follows() == [(editor, dataset, FollowOrigin.DISCUSSED)]

    def test_the_members_who_edited_follow_the_reuses_and_apis_they_edited(self):
        editor = UserFactory()
        organization = OrganizationFactory(editors=[editor])
        reuse = ReuseFactory(organization=organization)
        dataservice = DataserviceFactory(organization=organization)
        UserUpdatedReuse.objects.create(actor=editor, related_to=reuse, organization=organization)
        UserUpdatedDataservice.objects.create(
            actor=editor, related_to=dataservice, organization=organization
        )

        self.migrate(get_db())

        assert sorted(self.follows(), key=lambda row: row[1].__class__.__name__) == [
            (editor, dataservice, FollowOrigin.EDITED),
            (editor, reuse, FollowOrigin.EDITED),
        ]

    def test_deleted_users_follow_nothing(self):
        editor = UserFactory()
        organization = OrganizationFactory(editors=[editor])
        dataset = DatasetFactory(organization=organization)
        UserUpdatedDataset.objects.create(
            actor=editor, related_to=dataset, organization=organization
        )
        editor.mark_as_deleted(notify=False)

        self.migrate(get_db())

        assert self.follows() == []

    def test_having_edited_wins_over_having_discussed(self):
        editor = UserFactory()
        organization = OrganizationFactory(editors=[editor])
        dataset = DatasetFactory(organization=organization)
        UserUpdatedDataset.objects.create(
            actor=editor, related_to=dataset, organization=organization
        )
        DiscussionFactory(
            subject=dataset, user=editor, discussion=[MessageDiscussionFactory(posted_by=editor)]
        )

        self.migrate(get_db())

        assert self.follows() == [(editor, dataset, FollowOrigin.EDITED)]

    def test_sysadmins_follow_nothing(self):
        sysadmin = AdminFactory()
        organization = OrganizationFactory(editors=[sysadmin])
        edited, discussed = (
            DatasetFactory(organization=organization),
            DatasetFactory(organization=organization),
        )
        UserUpdatedDataset.objects.create(
            actor=sysadmin, related_to=edited, organization=organization
        )
        DiscussionFactory(
            subject=discussed,
            user=sysadmin,
            discussion=[MessageDiscussionFactory(posted_by=sysadmin)],
        )

        self.migrate(get_db())

        assert self.follows() == []

    def test_deleted_subjects_are_not_followed(self):
        """Datasets say `deleted`, dataservices `deleted_at`."""
        editor = UserFactory()
        organization = OrganizationFactory(editors=[editor])
        dataset = DatasetFactory(organization=organization, deleted=datetime.now(UTC))
        dataservice = DataserviceFactory(organization=organization, deleted_at=datetime.now(UTC))
        UserUpdatedDataset.objects.create(
            actor=editor, related_to=dataset, organization=organization
        )
        UserUpdatedDataservice.objects.create(
            actor=editor, related_to=dataservice, organization=organization
        )

        self.migrate(get_db())

        assert self.follows() == []
