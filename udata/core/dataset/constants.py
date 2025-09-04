from collections import OrderedDict

from udata.i18n import lazy_gettext as _

# Udata frequencies with their labels
#
# Based on the following vocabularies:
# - DC: http://dublincore.org/groups/collections/frequency/
# - EU: https://publications.europa.eu/en/web/eu-vocabularies/at-dataset/-/resource/dataset/frequency
UPDATE_FREQUENCIES = OrderedDict(
    [
        ("unknown", _("Unknown")),  #                      EU
        ("continuous", _("Real time")),  #                 DC, EU:UPDATE_CONT
        ("1min", _("Every minute")),  #                    EU
        ("5min", _("Every five minutes")),  #              EU
        ("10min", _("Every ten minutes")),  #              EU
        ("15min", _("Every fifteen minutes")),  #          EU
        ("30min", _("Every thirty minutes")),  #           EU
        ("hourly", _("Hourly")),  #                        EU
        ("bihourly", _("Every two hours")),  #             EU
        ("trihourly", _("Every three hours")),  #          EU
        ("12hours", _("Every twelve hours")),  #           EU:12HRS
        ("severalTimesADay", _("Several times a day")),  # EU:CONT
        ("threeTimesADay", _("Three times a day")),  #     EU:DAILY_3
        ("semidaily", _("Twice a day")),  #                EU:DAILY_2
        ("daily", _("Daily")),  #                          DC, EU
        ("fiveTimesAWeek", _("Five times a week")),  #     EU:WEEKLY_5
        ("threeTimesAWeek", _("Three times a week")),  #   DC, EU:WEEKLY_3
        ("semiweekly", _("Twice a week")),  #              DC, EU:WEEKLY_2
        ("weekly", _("Weekly")),  #                        DC, EU
        ("biweekly", _("Every two weeks")),  #             DC, EU
        ("threeTimesAMonth", _("Three times a month")),  # DC, EU:MONTHLY_3
        ("semimonthly", _("Twice a month")),  #            DC, EU:MONTHLY_2
        ("monthly", _("Monthly")),  #                      DC, EU
        ("bimonthly", _("Every two months")),  #           DC, EU
        ("quarterly", _("Quarterly")),  #                  DC, EU
        ("threeTimesAYear", _("Three times a year")),  #   DC, EU:ANNUAL_3
        ("semiannual", _("Twice a year")),  #              DC, EU:ANNUAL_2
        ("annual", _("Annually")),  #                      DC, EU
        ("biennial", _("Every two years")),  #             DC, EU
        ("triennial", _("Every three years")),  #          DC, EU
        ("quadrennial", _("Every four years")),  #         EU
        ("quinquennial", _("Every five years")),  #        EU
        ("decennial", _("Every ten years")),  #            EU
        ("bidecennial", _("Every twenty years")),  #       EU
        ("tridecennial", _("Every thirty years")),  #      EU
        ("punctual", _("Punctual")),  #                    EU:AS_NEEDED
        ("irregular", _("Irregular")),  #                  DC, EU:IRREG
        ("never", _("Never")),  #                          EU
        ("notPlanned", _("Not planned")),  #               EU:NOT_PLANNED
        ("other", _("Other")),  #                          EU
    ]
)

# Defined (not "unknown") but irregular or unquantifiable frequencies
UNBOUNDED_FREQUENCIES = [
    "continuous",
    "punctual",
    "irregular",
    "never",
    "notPlanned",
    "other",
]

BOUNDED_FREQUENCIES = [
    f for f in UPDATE_FREQUENCIES.keys() if f != "unknown" and f not in UNBOUNDED_FREQUENCIES
]

# Map legacy frequencies to current ones
LEGACY_FREQUENCIES = {
    "realtime": "continuous",
    "fourTimesADay": "severalTimesADay",
    "fourTimesAWeek": "other",
    "fortnighly": "biweekly",
    "biannual": "semiannual",
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
