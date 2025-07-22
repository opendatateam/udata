"""
This migration updates Topic.featured to False when it is None.
"""

import logging

import click

from udata.core.discussions.models import Discussion
from udata.mongo import db as udata_db

log = logging.getLogger(__name__)


def migrate(db):
    objects_with_discussions = Discussion.objects.aggregate(
        [{"$group": {"_id": "$subject._ref", "_cls": {"$first": "$subject._cls"}}}]
    )
    with click.progressbar(objects_with_discussions) as objects_with_discussions:
        for object in objects_with_discussions:
            related_to = udata_db.resolve_model(object["_cls"]).objects.get(pk=object["_id"].id)
            try:
                related_to.count_discussions()
            except Exception as err:
                log.error(f"Cannot count discussions for {object['_cls']} {object['_id'].id} {err}")
