from flask import request
from flask_security import current_user

from udata.auth import admin_permission


def current_user_is_admin_or_self() -> bool:
    if current_user.is_anonymous:
        return False
    return bool(request.endpoint == "api.me" or admin_permission.can())
