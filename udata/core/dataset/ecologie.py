from bson import ObjectId
from flask import current_app

from udata.commands import error, success
from udata.core.topic.models import Topic
from udata.models import Dataset
from udata.tasks import job

EXTRA_KEY = "ecologie:universe"


def get_topic_datasets_ids() -> list[ObjectId]:
    """Ids of the datasets in the ECOLOGIE_TOPIC_ID topic, empty if unset or not found."""
    topic_id = current_app.config.get("ECOLOGIE_TOPIC_ID")
    if not topic_id:
        error("ECOLOGIE_TOPIC_ID is not set, unflagging all datasets.")
        return []
    topic = Topic.objects(id=topic_id).first()
    if not topic:
        error(f"Topic {topic_id} not found, unflagging all datasets.")
        return []
    return [ObjectId(id) for id in topic.get_nested_elements_ids("Dataset")]


@job("map-ecologie-datasets")
def map_ecologie_datasets(self):
    """Flag the datasets of the ECOLOGIE_TOPIC_ID topic with the ecologie:universe extra."""
    ids = get_topic_datasets_ids()
    removed = Dataset.objects(**{f"extras__{EXTRA_KEY}__exists": True, "id__nin": ids}).update(
        **{f"unset__extras__{EXTRA_KEY}": True}
    )
    added = (
        Dataset.objects(**{"id__in": ids, f"extras__{EXTRA_KEY}__ne": True}).update(
            **{f"set__extras__{EXTRA_KEY}": True}
        )
        if ids
        else 0
    )
    success(f"Done. {added} dataset(s) flagged, {removed} unflagged, {len(ids)} in topic")
