from datetime import datetime

from flask import request
from flask_restx import marshal

from udata.api import API, api, fields
from udata.api_fields import patch
from udata.auth import current_user
from udata.core.organization.models import Organization
from udata.features.notifications.constants import FollowOrigin
from udata.features.notifications.events import is_event_name
from udata.features.notifications.permissions import EditNotificationPermission
from udata.mongo import db

from .models import Notification
from .settings import (
    NOTIFICATION_SCOPES,
    NotificationSetting,
    resolved_for,
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
            description="The organization to group the subject under",
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


@notifs.route("/settings/", endpoint="notification_settings")
class NotificationSettingsAPI(API):
    @api.secure
    @api.doc("list_notification_settings")
    @api.marshal_list_with(listed_setting_fields)
    def get(self):
        """List the rules the current user set about their notifications.

        Only rules are listed: whatever no rule covers follows the default rules. What
        they add up to is given by `/notifications/resolved/`."""
        return list(NotificationSetting.objects(user=current_user.id))

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
        setting it again replaces the previous answer."""
        rule = patch(NotificationSetting(user=current_user._get_current_object()), request)
        key = {
            "user": rule.user,
            "scope": rule.scope,
            "event": rule.event,
        }
        if rule.enabled is None:
            NotificationSetting.objects(**key).delete()
            return "", 204
        # Set by the user themselves: a follow created by an edit becomes their own.
        setting, created = NotificationSetting.objects.get_or_create(
            **key, updates={"enabled": rule.enabled, "origin": FollowOrigin.FOLLOWED}
        )
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
        "heard": fields.Boolean(description="Whether the user hears about it"),
        "reasons": fields.List(fields.String, description="Why the user is concerned"),
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
    cls, _, id = value.partition(":")
    if cls not in NOTIFICATION_SCOPES:
        api.abort(400, "Unknown subject")
    subject = db.resolve_model(cls).objects(id=id).first()
    if subject is None:
        api.abort(400, "Unknown subject")
    return subject


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
