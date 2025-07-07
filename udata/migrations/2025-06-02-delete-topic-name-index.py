"""Delete Topic index 'name_text'"""

import logging

from mongoengine.connection import get_db
from pymongo.errors import OperationFailure

log = logging.getLogger(__name__)


def migrate(db):
    log.info("Deleting index…")

    collection = get_db().topic

    try:
        collection.drop_index("name_text")
    except OperationFailure:
        log.info("Index does not exist?", exc_info=True)
