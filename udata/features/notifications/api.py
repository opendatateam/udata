from udata.api import API, api, fields
from udata.auth import current_user

from .actions import get_notifications

notifs = api.namespace("notifications", "Notifications API")

notifications_fields = api.model(
    "Notification",
    {
        "type": fields.String(description="The notification type", readonly=True),
        "created_on": fields.ISODateTime(
            description="The notification creation datetime", readonly=True
        ),
        "details": fields.Raw(
            description="Key-Value details depending on notification type", readonly=True
        ),
    },
)


@notifs.route("/", endpoint="notifications")
class NotificationsAPI(API):
    @api.secure
    @api.doc("get_notifications")
    @api.marshal_list_with(notifications_fields)
    def get(self):
        """List all current user pending notifications"""
        user = current_user._get_current_object()
        return get_notifications(user)
