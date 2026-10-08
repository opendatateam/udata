from datetime import datetime

from flask import request
from flask_restx import marshal
from flask_restx.inputs import boolean
from mongoengine import Q

from udata.api import API, add_pagination_arguments, api, fields
from udata.api_fields import patch
from udata.auth import current_user
from udata.core.organization.models import Organization
from udata.features.notifications.events import is_event_name
from udata.features.notifications.permissions import EditNotificationPermission

from .models import Notification
from .settings import (
    NOTIFICATION_SCOPES,
    NotificationSetting,
    resolved_for,
    set_follow,
    set_rule,
    subject_summary,
)

notifs = api.namespace("notifications", "Notifications API")


@notifs.route("/", endpoint="notifications")
class NotificationsAPI(API):
    @api.secure
    @api.doc("list_notifications")
    @api.expect(Notification.__index_parser__)
    @api.marshal_with(Notification.__page_fields__)
    def get(self):
        """List all current user pending notifications"""
        user = current_user._get_current_object()
        notifications = Notification.objects(user=user)
        return Notification.apply_pagination(Notification.apply_sort_filters(notifications))


subject_summary_fields = api.model(
    "NotificationSubjectSummary",
    {
        "title": fields.String(description="The subject title"),
        "page": fields.String(description="The subject web page"),
        "organization": fields.Nested(
            Organization.__ref_fields__,
            allow_null=True,
            description="The organization the subject belongs to, null for an organization",
        ),
    },
)

listed_setting_fields = api.inherit(
    "NotificationSettingListed",
    NotificationSetting.__read_fields__,
    {
        "subject": fields.Nested(
            subject_summary_fields,
            attribute=subject_summary,
            allow_null=True,
            description="The subject as the user may see it today, null once out of reach",
        ),
    },
)


listed_settings_page_fields = api.model(
    "NotificationSettingListedPage", fields.pager(listed_setting_fields)
)

# Paginated: editing or answering follows a subject, so the rules of a busy account
# keep growing, and each one reads its subject back.
settings_parser = add_pagination_arguments(api.parser(), page_size=20)
settings_parser.add_argument(
    "followed",
    type=boolean,
    location="args",
    help="Only the follows (a subject, yes), or only the other rules",
)


@notifs.route("/settings/", endpoint="notification_settings")
class NotificationSettingsAPI(API):
    @api.secure
    @api.doc("list_notification_settings")
    @api.expect(settings_parser)
    @api.marshal_with(listed_settings_page_fields)
    def get(self):
        """List the rules the current user set about their notifications, latest first.

        Only rules are listed: whatever no rule covers follows the default rules. What
        they add up to is given by `/notifications/resolved/`."""
        args = settings_parser.parse_args()
        settings = NotificationSetting.objects(user=current_user.id)
        if args["followed"] is True:
            settings = settings.filter(scope__ne=None, enabled=True)
        elif args["followed"] is False:
            settings = settings.filter(Q(scope=None) | Q(enabled=False))
        return settings.order_by("-id").paginate(args["page"], args["page_size"])

    @api.secure
    @api.doc("set_notification_setting")
    @api.expect(NotificationSetting.__write_fields__)
    # As listed, subject included: the screen adds the rule to its list as is.
    @api.response(200, "Rule replaced", listed_setting_fields)
    @api.response(201, "Rule created", listed_setting_fields)
    @api.response(204, "Rule removed, the broader rules or the defaults apply again")
    @api.response(400, "Validation error")
    def put(self):
        """Set a rule about some notifications, or remove it with `enabled: null`.

        A rule is identified by its subject and event, either of them possibly null:
        setting it again replaces the previous answer. Removing a follow udata made by
        itself (for editing a subject or answering about it) turns it into a "no", which
        comes back as a 200: removed, the next edit or answer would make it again."""
        rule = patch(NotificationSetting(user=current_user._get_current_object()), request)
        setting, created = set_rule(rule.user, rule.scope, rule.event, rule.enabled)
        if setting is None:
            return "", 204
        # Marshalled here rather than by `marshal_with`, which would also run the subject
        # of the empty 204 body through `subject_summary`.
        return marshal(setting, listed_setting_fields), 201 if created else 200


resolved_fields = api.model(
    "NotificationResolved",
    {
        "scope": fields.Nested(
            api.model_reference, allow_null=True, description="The subject asked about"
        ),
        "event": fields.String(allow_null=True, description="The event asked about"),
        "heard": fields.Boolean(description="Whether the user hears about it, pause aside"),
        "reasons": fields.List(fields.String, description="Why the user is concerned"),
        "muted": fields.Boolean(description="Whether the user said no to this subject and event"),
        "followed_events": fields.List(
            fields.String, description="The narrower events the user still follows on it"
        ),
    },
)

# A page asks for all of its subjects at once, each one costing a few queries.
MAX_RESOLVED_SUBJECTS = 100

resolved_parser = api.parser()
resolved_parser.add_argument(
    "scope",
    type=str,
    action="append",
    required=True,
    location="args",
    help=f"A subject, as `Class:id`, repeated for up to {MAX_RESOLVED_SUBJECTS} subjects",
)
resolved_parser.add_argument(
    "event",
    type=str,
    location="args",
    help="A notification type or a prefix of some, every notification without one",
)


def parse_subject(value: str):
    """A subject named `Class:id` in a query string, checked as one in a body."""
    class_name, _, id = value.partition(":")
    return api.resolve_reference(
        {"scope": {"class": class_name, "id": id}}, "scope", NOTIFICATION_SCOPES
    )


@notifs.route("/resolved/", endpoint="notification_resolved")
class NotificationResolvedAPI(API):
    @api.secure
    @api.doc("resolve_notifications")
    @api.expect(resolved_parser)
    @api.marshal_list_with(resolved_fields)
    @api.response(400, "Unknown subject or event, or too many subjects")
    def get(self):
        """Whether and why the current user hears about notifications on some
        subjects, once their rules and the defaults are applied.

        One answer per subject, so that a page asks once for all of its subjects. Without
        an event, it is about every notification on them."""
        args = resolved_parser.parse_args()
        if args["event"] is not None and not is_event_name(args["event"]):
            api.abort(400, "Unknown event")
        scopes = list(dict.fromkeys(args["scope"]))
        if len(scopes) > MAX_RESOLVED_SUBJECTS:
            api.abort(400, f"At most {MAX_RESOLVED_SUBJECTS} subjects")
        return resolved_for(
            current_user._get_current_object(),
            [parse_subject(scope) for scope in scopes],
            args["event"],
        )


follow_fields = api.model(
    "NotificationFollow",
    {
        "scope": fields.Nested(api.model_reference, required=True, description="The subject"),
        "event": fields.String(
            allow_null=True,
            description="A notification type or a prefix of some, every notification without one",
        ),
        "followed": fields.Boolean(required=True, description="Follow, or stop following"),
    },
)


@notifs.route("/follow/", endpoint="notification_follow")
class NotificationFollowAPI(API):
    @api.secure
    @api.doc("follow_notifications")
    @api.expect(follow_fields)
    @api.marshal_with(resolved_fields)
    @api.response(400, "Unknown subject or event")
    def put(self):
        """Follow some notifications on a subject, or stop, and get what the current user
        hears about once done.

        Which rules to write or withdraw depends on how they rank, which is the server's
        to know: stopping withdraws one's own follow, and only says no when a role or a
        broader follow still brings the notifications in."""
        payload = api.json_payload()
        event = payload.get("event")
        if not isinstance(payload.get("followed"), bool):
            api.abort(400, errors={"followed": "Expected true or false"})
        if event is not None and (not isinstance(event, str) or not is_event_name(event)):
            api.abort(400, errors={"event": "Unknown event"})
        return set_follow(
            current_user._get_current_object(),
            api.resolve_reference(payload, "scope", NOTIFICATION_SCOPES),
            event,
            payload["followed"],
        )


@notifs.route("/<notification:notification>/read/", endpoint="read_notifications")
class NotificationsReadAPI(API):
    @api.secure
    @api.doc("read_notification", responses={400: "Validation error"})
    @api.marshal_with(Notification.__read_fields__)
    def post(self, notification: Notification):
        """Read a notification."""
        EditNotificationPermission(notification).test()

        notification.handled_at = datetime.now()
        notification.save()

        return notification
