import logging

from udata.features.notifications.actions import notifier
from udata.models import Transfer

log = logging.getLogger(__name__)


@notifier("transfer_request")
def transfer_request_notifications(user):
    """Notify user about pending transfer requests"""
    orgs = [o for o in user.organizations if o.is_member(user)]
    notifications = []

    qs = Transfer.objects(recipient__in=[user] + orgs, status="pending")
    # Only fetch required fields for notification serialization
    # Greatly improve performances and memory usage
    qs = qs.only("id", "created", "subject")

    # Do not dereference subject (so it's a DBRef)
    # Also improve performances and memory usage
    for transfer in qs.no_dereference():
        notifications.append(
            (
                transfer.created,
                {
                    "id": transfer.id,
                    "subject": {
                        "class": transfer.subject["_cls"].lower(),
                        "id": transfer.subject["_ref"].id,
                    },
                },
            )
        )

    return notifications
