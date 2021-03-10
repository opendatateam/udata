from flask import request
from flask_security import current_user


def request_is_admin() -> bool:
    if 'me' in request.path or current_user.sysadmin:
        print('IN THE TRUE')
        return True
    print('ELSE')
    return False
