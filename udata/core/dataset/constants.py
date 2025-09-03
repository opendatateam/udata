from collections import OrderedDict

from udata.i18n import lazy_gettext as _

#: Udata frequencies with their labels
#:
#: Based on:
#: - DC vocabulary: http://dublincore.org/groups/collections/frequency/
#: - EU vocabulary: https://publications.europa.eu/en/web/eu-vocabularies/at-dataset/-/resource/dataset/frequency
UPDATE_FREQUENCIES = OrderedDict(
    [
        # FIXME: Drop end-of-line annotations
        ("unknown", _("Unknown")),  # udata default, EU only
        ("continuous", _("Real time")),  # EU "update_cont"
        ("1min", _("Every minute")),  # EU only
        ("5min", _("Every five minutes")),  # EU only
        ("10min", _("Every ten minutes")),  # EU only
        ("15min", _("Every fifteen minutes")),  # EU only
        ("30min", _("Every thirty minutes")),  # EU only
        ("hourly", _("Hourly")),  # ==
        ("bihourly", _("Every two hours")),  # EU only
        ("trihourly", _("Every three hours")),  # EU only
        ("12hrs", _("Every twelve hours")),  # EU only
        ("cont", _("Several times a day")),  # EU only
        #        ("fourTimesADay", _("Four times a day")),  # udata
        ("daily_3", _("Three times a day")),  # DC only "threeTimesADay"
        ("daily_2", _("Twice a day")),  # DC "semidaily"
        ("daily", _("Daily")),  # ==
        ("weekly_5", _("Five times a week")),  # EU only
        #        ("fourTimesAWeek", _("Four times a week")),  # udata
        ("weekly_3", _("Three times a week")),  # DC "threeTimesAWeek"
        ("weekly_2", _("Twice a week")),  # DC "semiweekly"
        ("weekly", _("Weekly")),  # ==
        ("biweekly", _("Every two weeks")),  # ==
        ("monthly_3", _("Three times a month")),  # DC "threeTimesAMonth"
        ("monthly_2", _("Twice a month")),  # DC "semimonthly"
        ("monthly", _("Monthly")),  # ==
        ("bimonthly", _("Every two months")),  # ==
        ("quarterly", _("Quarterly")),  # ==
        ("annual_3", _("Three times a year")),  # DC "threeTimesAYear"
        ("annual_2", _("Twice a year")),  # DC "semiannual"
        ("annual", _("Annually")),  # ==
        ("biennial", _("Every two years")),  # ==
        ("triennial", _("Every three years")),  # ==
        ("quadrennial", _("Every four years")),  # EU only
        ("quinquennial", _("Every five years")),  # EU only
        ("decennial", _("Every ten years")),  # EU only
        ("bidecennial", _("Every twenty years")),  # EU only
        ("tridecennial", _("Every thirty years")),  # EU only
        ("punctual", _("Punctual")),  # EU "as_needed"
        ("irregular", _("Irregular")),  # EU "irreg"
        ("never", _("Never")),  # EU only
        ("not_planned", _("Not planned")),  # EU only
        ("other", _("Other")),  # EU only
    ]
)

#: Map legacy frequencies to current ones
LEGACY_FREQUENCIES = {
    "realtime": "continuous",
    "fourTimesADay": "cont",
    "threeTimesADay": "daily_3",
    "semidaily": "daily_2",
    "fourTimesAWeek": "other",  # FIXME: or WEEKLY_3?
    "threeTimesAWeek": "weekly_3",
    "semiweekly": "weekly_2",
    "fortnighly": "biweekly",
    "threeTimesAMonth": "monthly_3",
    "semimonthly": "monthly_2",
    "threeTimesAYear": "annual_3",
    "semiannual": "annual_2",
    "biannual": "annual_2",
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
