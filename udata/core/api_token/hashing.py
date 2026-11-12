import hashlib
import hmac

from flask import current_app


# Apart from the models: `udata.api.oauth2` hashes its tokens too, and is itself imported while
# the models load.
def hash_token(plaintext):
    key = current_app.config["API_TOKEN_SECRET"].encode()
    return hmac.new(key, plaintext.encode(), hashlib.sha256).hexdigest()
