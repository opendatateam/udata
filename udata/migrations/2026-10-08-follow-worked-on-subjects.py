"""
Make every member who edited a dataset, a reuse or a dataservice of their organization,
or took part in the discussions of one of its subjects, follow it, as doing so now does.

The activities are the only record of who edited what, and they do not tell an edit made
by hand from one made by a script through an API key: both are attributed to the user.
Unlike at edit time, the accounts that publish through a script are therefore made to
follow what they published. Harvesting, attributed to `HARVEST_ACTIVITY_USER_ID`, is
left out, as it follows nothing at harvest time.

Membership is read as it is now, not as it was then: someone who left the organization
long ago does not start hearing about it again. Who is left out otherwise is the same
as at edit time (see `follow_worked_on`).

There are tens of millions of activities for about a hundred thousand pairs of a user and
a subject: the pairs are grouped by MongoDB, and everything needed to decide about them
is read once rather than per pair.
"""

import logging
from collections import defaultdict

from bson import DBRef, ObjectId
from flask import current_app
from pymongo.errors import BulkWriteError

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
from udata.core.discussions.models import Discussion
from udata.core.organization.models import Organization
from udata.core.reuse.activities import UserCreatedReuse, UserUpdatedReuse
from udata.core.reuse.models import Reuse
from udata.core.user.models import Role, User
from udata.features.notifications.constants import FollowOrigin
from udata.features.notifications.settings import NotificationSetting
from udata.mongo import db as mongo

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

DUPLICATE_KEY = 11000


def ref_id(value):
    return value.id if isinstance(value, DBRef) else value


def migrate(db):
    model_by_cls = {activity._class_name: model for activity, model in EDITS.items()}

    # (user id, model, subject id) -> origin. Having edited a subject says more than having
    # talked about it, so an edit wins.
    worked_on = {}

    log.info("Collecting who edited what from the activities...")
    edits = {"_cls": {"$in": list(model_by_cls)}, "actor._cls": "User"}
    # Harvesting is attributed to this account, and harvesting follows nothing.
    if harvester := current_app.config["HARVEST_ACTIVITY_USER_ID"]:
        edits["actor._ref"] = {"$ne": DBRef("user", ObjectId(harvester))}
    for row in Activity._get_collection().aggregate(
        [
            {"$match": edits},
            {
                "$group": {
                    "_id": {"user": "$actor._ref", "subject": "$related_to"},
                    "cls": {"$first": "$_cls"},
                }
            },
        ],
        allowDiskUse=True,
    ):
        key = (
            ref_id(row["_id"]["user"]),
            model_by_cls[row["cls"]],
            ref_id(row["_id"]["subject"]),
        )
        worked_on[key] = FollowOrigin.EDITED

    log.info("Collecting who took part in which discussions...")
    for row in Discussion._get_collection().aggregate(
        [
            {"$unwind": "$discussion"},
            {"$match": {"discussion.posted_by": {"$ne": None}}},
            {
                "$group": {
                    "_id": {
                        "user": "$discussion.posted_by",
                        "cls": "$subject._cls",
                        "subject": "$subject._ref",
                    }
                }
            },
        ],
        allowDiskUse=True,
    ):
        key = (
            row["_id"]["user"],
            mongo.resolve_model(row["_id"]["cls"]),
            ref_id(row["_id"]["subject"]),
        )
        worked_on.setdefault(key, FollowOrigin.DISCUSSED)
    log.info(f"{len(worked_on)} distinct subjects worked on found")

    # Sysadmins edit and answer on behalf of the platform, not of the organizations they
    # happen to belong to.
    admin = Role.objects(name="admin").first()
    eligible_users = {
        user["_id"]
        for user in User._get_collection().find(
            {"_id": {"$in": list({user_id for user_id, _, _ in worked_on})}},
            {"deleted": 1, "roles": 1},
        )
        if not user.get("deleted") and (admin is None or admin.id not in user.get("roles", []))
    }

    # Only the live subjects of an organization can be followed this way. Datasets and
    # reuses say `deleted`, dataservices `deleted_at`.
    subject_ids = defaultdict(set)
    for _, model, subject_id in worked_on:
        subject_ids[model].add(subject_id)
    organization_of = {}
    for model, ids in subject_ids.items():
        for subject in model._get_collection().find(
            {"_id": {"$in": list(ids)}, "organization": {"$ne": None}},
            {"organization": 1, "deleted": 1, "deleted_at": 1},
        ):
            if not (subject.get("deleted") or subject.get("deleted_at")):
                organization_of[(model, subject["_id"])] = subject["organization"]

    members = {
        organization["_id"]: {member["user"] for member in organization.get("members", [])}
        for organization in Organization._get_collection().find(
            {"_id": {"$in": list(set(organization_of.values()))}}, {"members.user": 1}
        )
    }

    # A decision already taken about the subject is left as is, so that having worked on
    # something one chose to ignore does not bring it back.
    decided = {
        (setting["user"], setting["scope"]["_ref"].id)
        for setting in NotificationSetting._get_collection().find(
            {"user": {"$in": list(eligible_users)}, "scope": {"$ne": None}},
            {"user": 1, "scope": 1},
        )
    }

    follows = [
        NotificationSetting(
            user=user_id, scope=model(pk=subject_id), enabled=True, origin=origin
        ).to_mongo()
        for (user_id, model, subject_id), origin in worked_on.items()
        if user_id in eligible_users
        and (model, subject_id) in organization_of
        and user_id in members.get(organization_of[(model, subject_id)], ())
        and (user_id, subject_id) not in decided
    ]

    created = len(follows)
    if follows:
        try:
            NotificationSetting._get_collection().insert_many(follows, ordered=False)
        except BulkWriteError as error:
            # The application keeps running meanwhile: a member editing one of these
            # subjects creates the same follow, which is then already there.
            errors = error.details["writeErrors"]
            if any(write_error["code"] != DUPLICATE_KEY for write_error in errors):
                raise
            created -= len(errors)

    log.info(f"Created {created} follows")
