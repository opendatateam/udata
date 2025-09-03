from collections import OrderedDict

from udata.i18n import lazy_gettext as _

# Udata frequencies with their labels
#
# Based on the following vocabularies:
# - DC: http://dublincore.org/groups/collections/frequency/
# - EU: https://publications.europa.eu/en/web/eu-vocabularies/at-dataset/-/resource/dataset/frequency
UPDATE_FREQUENCIES = OrderedDict(
    [
        ("unknown", _("Unknown")),  #                  EU
        ("continuous", _("Real time")),  #             DC, EU:UPDATE_CONT
        ("1min", _("Every minute")),  #                EU
        ("5min", _("Every five minutes")),  #          EU
        ("10min", _("Every ten minutes")),  #          EU
        ("15min", _("Every fifteen minutes")),  #      EU
        ("30min", _("Every thirty minutes")),  #       EU
        ("hourly", _("Hourly")),  #                    DC, EU
        ("bihourly", _("Every two hours")),  #         EU
        ("trihourly", _("Every three hours")),  #      EU
        ("12hrs", _("Every twelve hours")),  #         EU
        ("cont", _("Several times a day")),  #         EU
        ("daily_3", _("Three times a day")),  #        DC:threeTimesADay, EU
        ("daily_2", _("Twice a day")),  #              DC:semidaily, EU
        ("daily", _("Daily")),  #                      DC, EU
        ("weekly_5", _("Five times a week")),  #       EU
        ("weekly_3", _("Three times a week")),  #      DC:threeTimesAWeek, EU
        ("weekly_2", _("Twice a week")),  #            DC:semiweekly, EU
        ("weekly", _("Weekly")),  #                    DC, EU
        ("biweekly", _("Every two weeks")),  #         DC, EU
        ("monthly_3", _("Three times a month")),  #    DC:threeTimesAMonth, EU
        ("monthly_2", _("Twice a month")),  #          DC:semimonthly, EU
        ("monthly", _("Monthly")),  #                  DC, EU
        ("bimonthly", _("Every two months")),  #       DC, EU
        ("quarterly", _("Quarterly")),  #              DC, EU
        ("annual_3", _("Three times a year")),  #      DC:threeTimesAYear, EU
        ("annual_2", _("Twice a year")),  #            DC:semiannual, EU
        ("annual", _("Annually")),  #                  DC, EU
        ("biennial", _("Every two years")),  #         DC, EU
        ("triennial", _("Every three years")),  #      DC, EU
        ("quadrennial", _("Every four years")),  #     EU
        ("quinquennial", _("Every five years")),  #    EU
        ("decennial", _("Every ten years")),  #        EU
        ("bidecennial", _("Every twenty years")),  #   EU
        ("tridecennial", _("Every thirty years")),  #  EU
        ("punctual", _("Punctual")),  #                DC, EU:AS_NEEDED
        ("irregular", _("Irregular")),  #              DC, EU:IRREG
        ("never", _("Never")),  #                      EU
        ("not_planned", _("Not planned")),  #          EU
        ("other", _("Other")),  #                      EU
    ]
)

# Irregular or unquantifiable frequencies
UNBOUNDED_FREQUENCIES = set(
    [
        "unknown",
        "continuous",
        "punctual",
        "irregular",
        "never",
        "not_planned",
        "other",
    ]
)

# Map legacy frequencies to current ones
LEGACY_FREQUENCIES = {
    "realtime": "continuous",
    "fourTimesADay": "cont",
    "threeTimesADay": "daily_3",
    "semidaily": "daily_2",
    "fourTimesAWeek": "other",
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
