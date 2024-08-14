"""
The purpose here is to change the scopes attribute of
the OAuth2Client to scope without the s, then
to turn the list into a string.
"""

import logging

from mongoengine.connection import get_db

log = logging.getLogger(__name__)


def migrate(db):
    log.info("Processing OAuth2Client objects.")

    db = get_db()
    oauth_clients = db.oauth2_client
    oauth_clients.update_many({}, {"$rename": {"scopes": "scope"}})
    for client in oauth_clients.find():
        if type(client["scope"]) is list:
            scope_str = " ".join(client["scope"])
            client["scope"] = scope_str
            oauth_clients.save(client)

    log.info("Completed.")
