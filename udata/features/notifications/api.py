from datetime import datetime

from flask import request

from udata.api import API, api
from udata.api_fields import patch
from udata.auth import current_user
from udata.features.notifications.constants import NotificationChannel
from udata.features.notifications.permissions import EditNotificationPermission

from .models import Notification
from .settings import NotificationSetting

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


@notifs.route("/settings/", endpoint="notification_settings")
class NotificationSettingsAPI(API):
    @api.secure
    @api.doc("list_notification_settings")
    @api.marshal_list_with(NotificationSetting.__read_fields__)
    def get(self):
        """List the decisions the current user took about their notifications.

        Only decisions are listed: whatever is absent follows the defaults."""
        return list(NotificationSetting.objects(user=current_user.id))

    @api.secure
    @api.doc("set_notification_setting")
    @api.expect(NotificationSetting.__write_fields__)
    @api.marshal_with(NotificationSetting.__read_fields__)
    @api.response(400, "Validation error")
    def put(self):
        """Decide whether to hear about a family of notifications on a subject and a channel.

        A decision is identified by its subject, category and channel: deciding again
        replaces the previous answer."""
        decision = patch(NotificationSetting(user=current_user._get_current_object()), request)
        existing = NotificationSetting.objects(
            user=decision.user,
            scope=decision.scope,
            category=decision.category,
            channel=decision.channel,
        ).first()
        if existing is None:
            decision.save()
            return decision, 201
        existing.enabled = decision.enabled
        existing.save()
        return existing


@notifs.route("/settings/<notification_setting:setting>/", endpoint="notification_setting")
class NotificationSettingAPI(API):
    @api.secure
    @api.doc("delete_notification_setting")
    @api.response(204, "Decision removed, the default applies again")
    @api.response(404, "Decision not found")
    def delete(self, setting: NotificationSetting):
        """Withdraw a decision, so the default applies again."""
        if setting.user != current_user._get_current_object():
            api.abort(404, "Decision not found")
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
