from email_validator import EmailNotValidError, validate_email
from flask import current_app
from urlextract import URLExtract

from udata.i18n import lazy_gettext as _
from udata.mongo.errors import FieldValidationError

_url_extractor = URLExtract()


def check_no_urls(value, field, **_kwargs):
    if value and _url_extractor.find_urls(value):
        raise FieldValidationError(_("URLs not allowed in this field"), field=field)


def check_is_email(value, field, **_kwargs):
    if value:
        try:
            kwargs = current_app.config.get("SECURITY_EMAIL_VALIDATOR_ARGS", {}) or {}
            validate_email(value, **kwargs)
        except EmailNotValidError:
            raise FieldValidationError(_("Invalid email address"), field=field)
