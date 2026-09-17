from datetime import datetime

from udata.api import API, api
from udata.auth import current_user
from udata.features.notifications.constants import NotificationChannel
from udata.features.notifications.permissions import EditNotificationPermission

from .models import Notification

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
