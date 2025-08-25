from collections import OrderedDict

from udata.i18n import lazy_gettext as _

#: Udata frequencies with their labels
#:
#: See: http://dublincore.org/groups/collections/frequency/
UPDATE_FREQUENCIES = OrderedDict(
    [  # Dublin core equivalent
        ("unknown", _("Unknown")),  # N/A
        ("punctual", _("Punctual")),  # N/A
        ("continuous", _("Real time")),  # freq:continuous
        ("hourly", _("Hourly")),  # N/A
        ("fourTimesADay", _("Four times a day")),  # N/A
        ("threeTimesADay", _("Three times a day")),  # N/A
        ("semidaily", _("Semidaily")),  # N/A
        ("daily", _("Daily")),  # freq:daily
        ("fourTimesAWeek", _("Four times a week")),  # N/A
        ("threeTimesAWeek", _("Three times a week")),  # freq:threeTimesAWeek
        ("semiweekly", _("Semiweekly")),  # freq:semiweekly
        ("weekly", _("Weekly")),  # freq:weekly
        ("biweekly", _("Biweekly")),  # freq:bimonthly
        ("threeTimesAMonth", _("Three times a month")),  # freq:threeTimesAMonth
        ("semimonthly", _("Semimonthly")),  # freq:semimonthly
        ("monthly", _("Monthly")),  # freq:monthly
        ("bimonthly", _("Bimonthly")),  # freq:bimonthly
        ("quarterly", _("Quarterly")),  # freq:quarterly
        ("threeTimesAYear", _("Three times a year")),  # freq:threeTimesAYear
        ("semiannual", _("Biannual")),  # freq:semiannual
        ("annual", _("Annual")),  # freq:annual
        ("biennial", _("Biennial")),  # freq:biennial
        ("triennial", _("Triennial")),  # freq:triennial
        ("quinquennial", _("Quinquennial")),  # N/A
        ("irregular", _("Irregular")),  # freq:irregular
    ]
)

#: Map legacy frequencies to currents
LEGACY_FREQUENCIES = {
    "fortnighly": "biweekly",
    "biannual": "semiannual",
    "realtime": "continuous",
}

DEFAULT_FREQUENCY = "unknown"

DEFAULT_LICENSE = {
    "id": "notspecified",
    "title": "License Not Specified",
    "flags": ["generic"],
    "maintainer": None,
    "url": None,
    "active": True,
}

RESOURCE_TYPES = OrderedDict(
    [
        ("main", _("Main file")),
        ("documentation", _("Documentation")),
        ("update", _("Update")),
        ("api", _("API")),
        ("code", _("Code repository")),
        ("other", _("Other")),
    ]
)

RESOURCE_FILETYPE_FILE = "file"
RESOURCE_FILETYPES = OrderedDict(
    [
        (RESOURCE_FILETYPE_FILE, _("Uploaded file")),
        ("remote", _("Remote file")),
    ]
)

OGC_SERVICE_FORMATS = ["wms", "wfs"]

CHECKSUM_TYPES = ("sha1", "sha2", "sha256", "md5", "crc")
DEFAULT_CHECKSUM_TYPE = "sha1"

PIVOTAL_DATA = "pivotal-data"
CLOSED_FORMATS = ("pdf", "doc", "docx", "word", "xls", "excel", "xlsx")

# Maximum acceptable Damerau-Levenshtein distance
# used to guess license
# (ie. number of allowed character changes)
MAX_DISTANCE = 2

SCHEMA_CACHE_DURATION = 60 * 5  # In seconds

TITLE_SIZE_LIMIT = 350
DESCRIPTION_SIZE_LIMIT = 100000
DESCRIPTION_SHORT_SIZE_LIMIT = 200

FULL_OBJECTS_HEADER = "X-Get-Datasets-Full-Objects"
