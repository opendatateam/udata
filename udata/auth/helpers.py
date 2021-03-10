from flask import request
from flask_security import current_user


def request_is_admin() -> bool:
    if current_user.is_anonymous:
        return False
    if 'me' in request.path or current_user.sysadmin:
        return True
    return False
