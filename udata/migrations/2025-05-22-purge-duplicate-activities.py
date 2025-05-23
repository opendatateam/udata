"""
This migration updates Topic.featured to False when it is None.
"""

import logging
from datetime import datetime, timedelta

from udata.core.dataset.activities import UserCreatedDataset, UserDeletedDataset, UserUpdatedDataset
from udata.core.organization.activities import UserUpdatedOrganization
from udata.core.reuse.activities import UserCreatedReuse, UserDeletedReuse, UserUpdatedReuse
from udata.core.user.activities import (
    UserDiscussedDataset,
    UserDiscussedReuse,
    UserFollowedDataset,
    UserFollowedOrganization,
    UserFollowedReuse,
)

log = logging.getLogger(__name__)


def migrate(db):
    # Clean duplicate activities in case of discussion or following
    # - remove the "updated" activity on the discussed/followed object
    # - remove the activity on the organization
    # The heuristic is to look for specific activities by the same actor on the targeted object
    # within a -1 +1 second timespan
    for action_related_activity, object_updated_activity in [
        (UserDiscussedDataset, UserUpdatedDataset),
        (UserDiscussedReuse, UserUpdatedReuse),
        (UserFollowedDataset, UserUpdatedDataset),
        (UserFollowedReuse, UserUpdatedReuse),
    ]:
        org_activity_count = 0
        object_activity_count = 0
        activities = (
            action_related_activity.objects()
            .order_by("-created_at")
            .no_dereference()  # We use no_dereference in query to prevent DBref DoesNotExist errors
            .no_cache()
        )
        log.info(
            f"{datetime.utcnow()}: Processing {activities.count()} {action_related_activity} activities..."
        )
        for act in activities:
            object_activity_count += object_updated_activity.objects(
                actor=act.actor.id,
                related_to=act.related_to.id,
                created_at__gte=act.created_at - timedelta(seconds=1),
                created_at__lte=act.created_at + timedelta(seconds=1),
            ).count()
            org_activity_count += UserUpdatedOrganization.objects(
                actor=act.actor.id,
                created_at__gte=act.created_at - timedelta(seconds=1),
                created_at__lte=act.created_at + timedelta(seconds=1),
            ).count()
        log.info(
            f"{datetime.utcnow()}: Deleted {object_activity_count} {object_updated_activity} and {org_activity_count} UserUpdatedOrganization activities"
        )

    # Clean duplicated UserUpdatedOrganization activities on organization for any object related activity
    for object_related_activity in [
        UserCreatedDataset,
        UserUpdatedDataset,
        UserDeletedDataset,
        UserCreatedReuse,
        UserUpdatedReuse,
        UserDeletedReuse,
        UserFollowedOrganization,
    ]:
        count = 0
        activities = (
            object_related_activity.objects()
            .order_by("-created_at")
            .no_dereference()  # We use no_dereference in query to prevent DBref DoesNotExist errors
            .no_cache()
        )
        log.info(
            f"{datetime.utcnow()}: Processing {activities.count()} {object_related_activity} activities..."
        )
        for act in activities:
            count += UserUpdatedOrganization.objects(
                actor=act.actor.id,
                created_at__gte=act.created_at - timedelta(seconds=1),
                created_at__lte=act.created_at + timedelta(seconds=1),
            ).count()
        log.info(f"{datetime.utcnow()}: Deleted {count} UserUpdatedOrganization activities")
