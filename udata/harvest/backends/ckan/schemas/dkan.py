import dateutil.parser
from humanfriendly import parse_size
from voluptuous import All, Any, DefaultTo, Lower, Optional, Schema

from udata.harvest.filters import boolean, email, empty_none, hash, is_url, normalize_string, slug

from .ckan import tag


class FrenchParserInfo(dateutil.parser.parserinfo):
    WEEKDAYS = [
        ("Lun", "Lundi"),
        ("Mar", "Mardi"),
        ("Mer", "Mercredi"),
        ("Jeu", "Jeudi"),
        ("Ven", "Vendredi"),
        ("Sam", "Samedi"),
        ("Dim", "Dimanche"),
    ]


def parse_date(value, **kwargs):
    return dateutil.parser.parse(value, **kwargs).date()


def to_date(value):
    """
    Try w/ french weekdays then dateutil's default
    `fuzzy` is used when 'Date changed' is in the value
    """
    try:
        return parse_date(value, fuzzy=True, parserinfo=FrenchParserInfo(), dayfirst=True)
    except ValueError:
        return parse_date(value, fuzzy=True)


def dkan_parse_size(value):
    if value:
        # not strictly true but should be enough
        value = value.replace("octets", "bytes")
        return parse_size(value)


resource = {
    "id": str,
    "name": All(DefaultTo(""), str),
    "description": All(str, normalize_string),
    "format": All(str, Lower),
    "mimetype": Any(All(str, Lower), None),
    "size": All(str, dkan_parse_size),
    Optional("hash"): Any(All(str, hash), None),
    "created": All(str, to_date),
    "last_modified": Any(All(str, to_date), None),
    "url": All(str, is_url()),
    Optional("resource_type", default="dkan"): All(
        empty_none,
        str,
    ),
}

group = {
    "id": str,
    "description": str,
    "image_display_url": str,
    "title": str,
    "name": All(str, slug),
}

schema = Schema(
    {
        "id": str,
        "name": str,
        "title": str,
        "notes": Any(All(str, normalize_string), None),
        Optional("license_id", default=None): All(DefaultTo("not-specified"), str),
        Optional("license_title", default=None): Any(str, None),
        Optional("tags", default=list): [tag],
        "metadata_created": All(str, to_date),
        "metadata_modified": All(str, to_date),
        Optional("groups"): [Any(group, None)],
        "resources": [resource],
        Optional("extras", default=list): [
            {
                "key": str,
                "value": Any(str, int, float, boolean, dict, list),
            }
        ],
        "private": boolean,
        "type": "Dataset",
        Optional("author"): Any(str, None),
        Optional("author_email"): All(empty_none, Any(All(str, email), None)),
        "maintainer": Any(str, None),
        "maintainer_email": All(empty_none, Any(All(str, email), None)),
        "state": Any(str, None),
    },
    required=True,
    extra=True,
)
