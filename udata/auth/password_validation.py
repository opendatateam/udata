import re
import unicodedata

from flask import current_app

from udata.i18n import lazy_gettext as _


class UdataPasswordUtil:

    def __init__(self, app):
        pass

    @staticmethod
    def normalize(password):
        cf = current_app.config.get('SECURITY_PASSWORD_NORMALIZE_FORM')
        if cf:
            return unicodedata.normalize(cf, password)
        return password

    def validate(self, password, is_register, **kwargs):
        pnorm = self.normalize(password)

        error_list = []
        pass_length = current_app.config.get('SECURITY_PASSWORD_LENGTH_MIN')
        if len(pnorm) < pass_length:
            message = _('Password must be at least {pass_length} characters long')
            error_list.append(message.format(pass_length=pass_length))

        # searching for lowercase
        if current_app.config.get('SECURITY_PASSWORD_REQUIREMENTS_LOWERCASE') and (
                re.search(r"[a-z]", pnorm) is None):
            error_list.append(_('Password must contain lowercases'))

        # searching for digits
        if current_app.config.get('SECURITY_PASSWORD_REQUIREMENTS_DIGITS') and (re.search(r"\d", pnorm) is None):
            error_list.append(_('Password must contain digits'))

        # searching for uppercase
        if current_app.config.get('SECURITY_PASSWORD_REQUIREMENTS_UPPERCASE') and (
                re.search(r"[A-Z]", pnorm) is None):
            error_list.append(_('Password must contain uppercases'))

        # searching for symbols
        if current_app.config.get('SECURITY_PASSWORD_REQUIREMENTS_SYMBOLS') and (
                re.search(r"[ !#$%&'()*+,-./[\\\]^_`{|}~" + r'"]', pnorm) is None):
            error_list.append(_('Password must contain symbols'))

        return error_list, pnorm
