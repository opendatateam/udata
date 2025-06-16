from collections import OrderedDict

from udata.i18n import lazy_gettext as _

#: Udata frequencies with their labels
#:
#: See: https://publications.europa.eu/en/web/eu-vocabularies/at-dataset/-/resource/dataset/frequency
UPDATE_FREQUENCIES = OrderedDict(
    [
        # FIXME: Add ALL EU terms (from 30yrs to 1mn)?
        # FIXME: Uppercase to match EU vocab?
        # FIXME: Drop end-of-line annotations
        ("unknown", _("Unknown")),  # =
        ("other", _("Other")),  # N/A
        ("never", _("Never")),  # N/A
        ("not_planned", _("Not planned")),  # N/A
        ("as_needed", _("As needed")),  # punctual
        ("irreg", _("Irregular")),  # irregular
        ("update_cont", _("Real time")),  # continuous
        ("hourly", _("Hourly")),  # =
        ("cont", _("Several times a day")),  # N/A
        ("daily_2", _("Semidaily")),  # semidaily
        ("daily", _("Daily")),  # =
        ("weekly_5", _("Five times a week")),  # N/A
        ("weekly_3", _("Three times a week")),  # threeTimesAWeek
        ("weekly_2", _("Semiweekly")),  # semiweekly
        ("weekly", _("Weekly")),  # =
        ("biweekly", _("Biweekly")),  # =
        ("monthly_3", _("Three times a month")),  # threeTimesAMonth
        ("monthly_2", _("Semimonthly")),  # semimonthly
        ("monthly", _("Monthly")),  # =
        ("bimonthly", _("Bimonthly")),  # =
        ("quarterly", _("Quarterly")),  # =
        ("annual_3", _("Three times a year")),  # threeTimesAYear
        ("annual_2", _("Biannual")),  # semiannual
        ("annual", _("Annual")),  # =
        ("biennial", _("Biennial")),  # =
        ("triennial", _("Triennial")),  # =
        ("quinquennial", _("Quinquennial")),  # =
        ("decennial", _("Decennial")),  # N/A
    ]
)

#: Map legacy (including DC) frequencies to currents
LEGACY_FREQUENCIES = {
    # FIXME: Preserve older mappings?
    "irregular": "irreg",
    "punctual": "as_needed",
    "realtime": "update_cont",
    "continuous": "update_cont",
    "fourTimesADay": "cont",  # FIXME: or OTHER?
    "threeTimesADay": "cont",  # FIXME: or OTHER?
    "semidaily": "daily_2",
    "fourTimesAWeek": "other",  # FIXME: or WEEKLY_3?
    "threeTimesAWeek": "weekly_3",
    "semiweekly": "weekly_2",
    "threeTimesAMonth": "monthly_3",
    "semimonthly": "monthly_2",
    "fortnighly": "biweekly",
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

FULL_OBJECTS_HEADER = "X-Get-Datasets-Full-Objects"
