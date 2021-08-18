import json
import hmac


def sign(msg, secret):
    if isinstance(secret, str):
        secret = secret.encode('utf-8')
    if isinstance(msg, (dict, tuple, list)):
        msg = json.dumps(msg).encode('utf-8')
    return hmac.new(secret, msg, 'sha256').hexdigest()
