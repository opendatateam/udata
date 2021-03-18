from flask import request
from flask_security import current_user


def current_user_is_admin_or_self() -> bool:
    if current_user.is_anonymous:
        return False
    if 'me' in request.path or current_user.sysadmin:
        return True
    return False
