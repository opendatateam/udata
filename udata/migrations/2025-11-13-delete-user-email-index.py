"""Delete Topic index 'name_text'"""

import logging

from mongoengine.connection import get_db
from pymongo.errors import OperationFailure

from udata.models import User

log = logging.getLogger(__name__)


def migrate(db):
    log.info("Deleting index…")

    collection = get_db().user

    # Remove previous index
    try:
        collection.drop_index("slug_text")
    except OperationFailure:
        log.info("Index `slug_text` does not exist?", exc_info=True)

    # Force new index creation (before old code in workers recreate it?)
    User.objects.first()
