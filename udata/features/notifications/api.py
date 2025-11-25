from udata.api import API, api
from udata.auth import current_user

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
        notifications = Notification.objects(user=user)
        return Notification.apply_pagination(Notification.apply_sort_filters(notifications))
