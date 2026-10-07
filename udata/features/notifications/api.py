from datetime import datetime

from flask import request

from udata.api import API, api, fields
from udata.api_fields import patch
from udata.auth import current_user
from udata.core.organization.models import Organization
from udata.features.notifications.constants import DEFAULT_ENABLED, NotificationChannel
from udata.features.notifications.permissions import EditNotificationPermission

from .models import Notification
from .settings import CONFIGURABLE_REASONS, NotificationSetting, subject_summary

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
        # Rows that only carry MAIL belong to somebody who muted the bell and asked for
        # a digest: they exist to be summarized, not to be shown here.
        notifications = Notification.objects(user=user, channels=NotificationChannel.APP)
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

        Only rules are listed: whatever no rule covers follows the defaults of the
        reasons the user is concerned for (see `/notifications/reasons/`)."""
        return list(NotificationSetting.objects(user=current_user.id))

    @api.secure
    @api.doc("set_notification_setting")
    @api.expect(NotificationSetting.__write_fields__)
    @api.marshal_with(NotificationSetting.__read_fields__)
    @api.response(400, "Validation error")
    def put(self):
        """Set a rule about some notifications.

        A rule is identified by its subject, event, reason and channel, any of them
        possibly null: setting it again replaces the previous answer."""
        rule = patch(NotificationSetting(user=current_user._get_current_object()), request)
        setting, created = NotificationSetting.objects.get_or_create(
            user=rule.user,
            scope=rule.scope,
            event=rule.event,
            reason=rule.reason,
            channel=rule.channel,
            updates={"enabled": rule.enabled},
        )
        return setting, 201 if created else 200


reason_fields = api.model(
    "NotificationReasonDefault",
    {
        "reason": fields.String(description="Why a user can be concerned by a notification"),
        "default": fields.Boolean(
            description="Whether somebody concerned for this reason hears about it without any rule"
        ),
    },
)


@notifs.route("/reasons/", endpoint="notification_reasons")
class NotificationReasonsAPI(API):
    @api.doc("list_notification_reasons")
    @api.marshal_list_with(reason_fields)
    def get(self):
        """The configurable reasons, with what each one gets without any rule."""
        return [
            {"reason": reason, "default": DEFAULT_ENABLED[reason]} for reason in CONFIGURABLE_REASONS
        ]


@notifs.route("/settings/<notification_setting:setting>/", endpoint="notification_setting")
class NotificationSettingAPI(API):
    @api.secure
    @api.doc("delete_notification_setting")
    @api.response(204, "Rule removed, the broader rules or the defaults apply again")
    @api.response(404, "Rule not found")
    def delete(self, setting: NotificationSetting):
        """Remove a rule, so the broader rules or the defaults apply again."""
        if setting.user != current_user._get_current_object():
            api.abort(404, "Rule not found")
        setting.delete()
        return "", 204


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
