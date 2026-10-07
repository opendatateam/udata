"""
Make every member who edited a dataset, a reuse or a dataservice of their organization
follow it, as editing one now does.

The activities are the only record of who edited what. Only the activities of a user
count: once an activity can be attributed to the API token that performed it, the
edits made by a script are left out, as they are at edit time.

Membership is read as it is now, not as it was then: someone who left the organization
long ago does not start hearing about it again.
"""

import logging

from bson import DBRef

from udata.core.activity.models import Activity
from udata.core.dataservices.activities import UserCreatedDataservice, UserUpdatedDataservice
from udata.core.dataservices.models import Dataservice
from udata.core.dataset.activities import (
    UserAddedResourceToDataset,
    UserCreatedDataset,
    UserRemovedResourceFromDataset,
    UserUpdatedDataset,
    UserUpdatedResource,
)
from udata.core.dataset.models import Dataset
from udata.core.reuse.activities import UserCreatedReuse, UserUpdatedReuse
from udata.core.reuse.models import Reuse
from udata.core.user.models import User
from udata.features.notifications.follow import follow_worked_on

log = logging.getLogger(__name__)

EDITS = {
    UserCreatedDataset: Dataset,
    UserUpdatedDataset: Dataset,
    UserAddedResourceToDataset: Dataset,
    UserUpdatedResource: Dataset,
    UserRemovedResourceFromDataset: Dataset,
    UserCreatedReuse: Reuse,
    UserUpdatedReuse: Reuse,
    UserCreatedDataservice: Dataservice,
    UserUpdatedDataservice: Dataservice,
}


def ref_id(value):
    return value.id if isinstance(value, DBRef) else value


def migrate(db):
    model_by_cls = {activity._class_name: model for activity, model in EDITS.items()}

    log.info("Collecting who edited what from the activities...")
    edits = set()
    for activity in (
        Activity.objects(_cls__in=list(model_by_cls))
        .only("actor", "related_to")
        .as_pymongo()
        .batch_size(1000)
    ):
        actor = activity.get("actor")
        if not isinstance(actor, dict) or actor.get("_cls") != "User":
            continue
        edits.add((ref_id(actor["_ref"]), model_by_cls[activity["_cls"]], ref_id(activity["related_to"])))
    log.info(f"{len(edits)} distinct edits found")

    before = db.notification_setting.count_documents({})
    for user_id, model, subject_id in edits:
        user = User.objects(id=user_id).first()
        subject = model.objects(id=subject_id).first()
        # Datasets and reuses say `deleted`, dataservices `deleted_at`.
        subject_deleted = subject is not None and (
            getattr(subject, "deleted", None) or getattr(subject, "deleted_at", None)
        )
        if user is None or user.deleted or subject is None or subject_deleted:
            continue
        follow_worked_on(user, subject)

    log.info(f"Created {db.notification_setting.count_documents({}) - before} follows")
