import re

from flask import current_app

from udata.i18n import lazy_gettext as _


def password_validator(password, is_register, **kwargs):
    error_list = []
    # calculating the length
    if len(password) < current_app.config.get('SECURITY_PASSWORD_LENGTH_MIN'):
        error_list.append(_('Password too short'))

    # searching for lowercase
    if current_app.config.get('SECURITY_PASSWORD_REQUIREMENTS_LOWERCASE') and (re.search(r"[a-z]", password) is None):
        error_list.append(_('Password must contain lowercases'))

    # searching for digits
    if current_app.config.get('SECURITY_PASSWORD_REQUIREMENTS_DIGITS') and (re.search(r"\d", password) is None):
        error_list.append(_('Password must contain digits'))

    # searching for uppercase
    if current_app.config.get('SECURITY_PASSWORD_REQUIREMENTS_UPPERCASE') and (re.search(r"[A-Z]", password) is None):
        error_list.append(_('Password must contain uppercases'))

    # searching for symbols
    if current_app.config.get('SECURITY_PASSWORD_REQUIREMENTS_SYMBOLS') and (re.search(r"[ !#$%&'()*+,-./[\\\]^_`{|}~"+r'"]', password) is None):
        error_list.append(_('Password must contain symbols'))

    if error_list:
        return error_list
    return None
