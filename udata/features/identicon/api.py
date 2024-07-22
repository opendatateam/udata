from udata.api import API, api

from . import backends

ns = api.namespace("avatars", "Avatars")


@ns.route("/<identifier>/<int:size>", endpoint="avatar")
class IdenticonAPI(API):
    @api.doc("avatars")
    def get(self, identifier, size):
        """Get a deterministic avatar given an identifier at a given size"""
        return backends.get_identicon(identifier, size)
