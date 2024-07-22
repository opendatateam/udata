import logging

from udata.features.notifications.actions import notifier

log = logging.getLogger(__name__)


@notifier("membership_request")
def membership_request_notifications(user):
    """Notify user about pending membership requests"""
    orgs = [o for o in user.organizations if o.is_admin(user)]
    notifications = []

    for org in orgs:
        for request in org.pending_requests:
            notifications.append(
                (
                    request.created,
                    {
                        "id": request.id,
                        "organization": org.id,
                        "user": {
                            "id": request.user.id,
                            "fullname": request.user.fullname,
                            "avatar": str(request.user.avatar),
                        },
                    },
                )
            )

    return notifications
