from flask import current_app
from urlextract import URLExtract

from udata.auth.password_validation import UdataPasswordUtil
from udata.i18n import lazy_gettext as _
from udata.mongo.errors import FieldValidationError


def password_rules(value, *, is_creation, field, **kwargs):
    if not value:
        if is_creation:
            raise FieldValidationError(field=field, message=_("Password not provided"))
        return

    password_util = UdataPasswordUtil(current_app)
    errors, _normalized = password_util.validate(value, is_register=is_creation)
    if errors:
        raise FieldValidationError(field=field, message=errors[0])


def confirmed(value, *, field, request_data, **kwargs):
    if not value:
        return

    confirmation_field = f"{field}_confirmation"
    confirmation_value = request_data.get(confirmation_field)

    if value != confirmation_value:
        raise FieldValidationError(field=confirmation_field, message=_("Passwords do not match"))


def no_urls(value, *, field, **kwargs):
    if not value:
        return

    extractor = URLExtract()
    urls = extractor.find_urls(value)
    if urls:
        raise FieldValidationError(field=field, message=_("URLs not allowed in this field"))
