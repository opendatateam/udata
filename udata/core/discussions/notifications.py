from udata.features.notifications.actions import notifier

from .actions import discussions_for


import logging

log = logging.getLogger(__name__)


@notifier('discussion')
def discussions_notifications(user):
    '''Notify user about open discussions'''
    notifications = []

    # Only fetch required fields for notification serialization
    # Greatly improve performances and memory usage
    qs = discussions_for(user).only('id', 'created', 'title', 'subject')

    # Do not dereference subject (so it's a DBRef)
    # Also improve performances and memory usage
    for discussion in qs.no_dereference():
        notifications.append((discussion.created, {
            'id': discussion.id,
            'title': discussion.title,
            'subject': {
                'id': discussion.subject['_ref'].id,
                'type': discussion.subject['_cls'].lower(),
            }
        }))

    return notifications
