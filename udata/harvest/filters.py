import dateutil.parser
from voluptuous import Invalid

from udata import tags, uris

TRUTHY_STRINGS = ("on", "t", "true", "y", "yes", "1")
FALSY_STRINGS = ("f", "false", "n", "no", "off", "0")


def boolean(value):
    """
    Convert the content of a string (or a number) to a boolean.
    Do nothing when input value is already a boolean.

    This filter accepts usual values for ``True`` and ``False``:
    "0", "f", "false", "n", etc.
    """
    if value is None or isinstance(value, bool):
        return value

    if isinstance(value, int):
        return bool(value)

    if isinstance(value, str):
        lower_value = value.strip().lower()

        if not lower_value:
            return None
        if lower_value in FALSY_STRINGS:
            return False
        if lower_value in TRUTHY_STRINGS:
            return True
        raise Invalid(
            f"Unable to parse string '{value}' as boolean. Supported values are {','.join(TRUTHY_STRINGS)} for `True` and {','.join(FALSY_STRINGS)} for `False`."
        )

    raise Invalid(
        f"Cannot convert value {value} of type {type(value)} to boolean. Supported types are `bool`, `int` and `str`"
    )


def to_date(value):
    """Parse a date"""
    return dateutil.parser.parse(value).date()


def email(value):
    """Validate an email"""
    if "@" not in value:
        raise Invalid("This email is invalid.")
    return value


def force_list(value):
    """
    Ensure single elements are wrapped into list
    """
    if not isinstance(value, (list, tuple)):
        return [value]
    return value


def slug(value):
    return tags.slug(value)


def normalize_tag(value):
    return tags.normalize(value)


def taglist(value):
    return tags.tags_list(value)


def empty_none(value):
    """Replace falsy values with None"""
    return value if value else None


def strip(value):
    """Strip spaces from a string and remove it when empty."""
    return empty_none(value.strip())


def line_endings(value):
    """Replaces CR + LF or CR to LF in a string,
    then strip spaces and remove it when empty.
    """
    return value.replace("\r\n", "\n").replace("\r", "\n")


def normalize_string(value):
    return strip(line_endings(value))


def is_url(default_scheme="http", **kwargs):
    """Return a converter that converts a clean string to an URL."""

    def converter(value):
        if value is None:
            return value
        if "://" not in value and default_scheme:
            value = "://".join((default_scheme, value.strip()))
        try:
            return uris.validate(value)
        except uris.ValidationError as e:
            raise Invalid(str(e))

    return converter


def hash(value):
    """Detect an hash type"""
    if not value:
        return
    elif len(value) == 32:
        type = "md5"
    elif len(value) == 40:
        type = "sha1"
    elif len(value) == 64:
        type = "sha256"
    else:
        return None
    return {"type": type, "value": value}
