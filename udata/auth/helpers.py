from flask_security import current_user


def request_is_admin() -> bool:
    if current_user.is_anonymous or not current_user.sysadmin:
        return False
    return True
