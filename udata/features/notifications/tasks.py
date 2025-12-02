import logging
from datetime import datetime, timedelta

from flask import current_app

from udata.features.notifications.models import Notification
from udata.tasks import job

log = logging.getLogger(__name__)


@job("delete-expired-notifications")
def delete_expired_notifications(self):
    # Delete expired notifications
    handled_at = datetime.utcnow() - timedelta(
        days=current_app.config["DAYS_AFTER_NOTIFICATION_EXPIRED"]
    )
    notifications_to_delete = Notification.objects(
        handled_at__lte=handled_at,
    )
    count = notifications_to_delete.count()
    for notification in notifications_to_delete:
        notification.delete()

    log.info(f"Deleted {count} expired notifications")
