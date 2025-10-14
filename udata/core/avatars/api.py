import hashlib
import io

import pydenticon
from flask import current_app, send_file

from udata.api import API, api
from udata.app import cache

ns = api.namespace("avatars", "Avatars")


@cache.memoize()
def generate_pydenticon(identifier, size):
    """
    Use pydenticon to generate an identicon image.
    All parameters are extracted from configuration.
    """
    blocks_size = current_app.config["AVATAR_INTERNAL_SIZE"]
    foreground = current_app.config["AVATAR_INTERNAL_FOREGROUND"]
    background = current_app.config["AVATAR_INTERNAL_BACKGROUND"]
    generator = pydenticon.Generator(
        blocks_size, blocks_size, digest=hashlib.sha1, foreground=foreground, background=background
    )

    # Pydenticon adds padding to the size and as a consequence
    # we need to compute the size without the padding
    padding = int(round(current_app.config["AVATAR_INTERNAL_PADDING"] * size / 100.0))
    size = size - 2 * padding
    padding = (padding,) * 4
    return generator.generate(identifier, size, size, padding=padding, output_format="png")


@ns.route("/<identifier>/<int:size>/", endpoint="avatar")
class IdenticonAPI(API):
    @api.doc("avatars")
    def get(self, identifier, size):
        """Get a deterministic avatar given an identifier at a given size"""
        identicon = generate_pydenticon(identifier, size)
        response = send_file(io.BytesIO(identicon), mimetype="image/png")
        etag = hashlib.sha1(identicon).hexdigest()
        response.set_etag(etag)
        return response
