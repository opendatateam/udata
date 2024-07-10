"""
Set fs_uniquifier field for every user due to Flask-Security-Too update > v4.0.0
"""

import logging
import uuid

from mongoengine.errors import ValidationError

from udata.models import User

log = logging.getLogger(__name__)


def migrate(db):
    log.info("Processing Users fs_uniquifier attribute.")

    users = User.objects().no_cache().timeout(False)
    for user in users:
        user.fs_uniquifier = uuid.uuid4().hex
        try:
            user.save()
        except ValidationError as e:
            log.error(f"Error on user {user.id}: {e}")

    log.info("Completed.")
