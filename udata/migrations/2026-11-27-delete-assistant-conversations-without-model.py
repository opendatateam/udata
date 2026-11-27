"""
Delete the assistant conversations stored without their model.

A conversation now keeps the model it started with, in `ai_model`. Those stored before have
none: they could go on with another model, which would read the history of the first one.
The client starts a new conversation each time it opens the assistant, so none is reopened.
"""

import logging

log = logging.getLogger(__name__)


def migrate(db):
    result = db.assistant_conversation.delete_many({"ai_model": None})
    log.info(f"Deleted {result.deleted_count} assistant conversations without a model")
