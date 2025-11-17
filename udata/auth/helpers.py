from flask import abort, request
from flask_login import login_user
from flask_security import current_user
from flask_security.utils import set_request_attr


def current_user_is_admin_or_self() -> bool:
    if current_user.is_anonymous:
        return False
    if request.endpoint == "api.me" or current_user.sysadmin:
        return True
    return False


def login_from_apikey_header_if_exists():
    from udata.models import User

    apikey = request.headers.get("X-API-KEY")
    if not apikey:
        return False

    try:
        user = User.objects.get(apikey=apikey)

        if not login_user(user, remember=False, duration=None, force=True, fresh=True):
            abort(401, "Inactive user")

        # Useful because otherwise Flask-Security refuse the connection.
        set_request_attr("fs_authn_via", "token")

        return True
    except User.DoesNotExist:
        abort(401, "Invalid API Key")
