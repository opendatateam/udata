from collections import OrderedDict
from datetime import datetime, timedelta
from enum import StrEnum, auto

from flask_babel import LazyString

from udata.i18n import lazy_gettext as _


class UpdateFrequency(StrEnum):
    """
    Udata frequency vocabulary

    Based on the following vocabularies:
    - DC: http://dublincore.org/groups/collections/frequency/
    - EU: https://publications.europa.eu/en/web/eu-vocabularies/at-dataset/-/resource/dataset/frequency
    """

    CONTINUOUS = auto(), _("Real time"), None  # DC, EU:UPDATE_CONT
    ONE_MINUTE = "oneMinute", _("Every minute"), timedelta(minutes=1)  # EU:1MIN
    FIVE_MINUTES = "fiveMinutes", _("Every five minutes"), timedelta(minutes=5)  # EU:5MIN
    TEN_MINUTES = "tenMinutes", _("Every ten minutes"), timedelta(minutes=10)  # EU:10MIN
    FIFTEEN_MINUTES = (
        "fifteenMinutes",
        _("Every fifteen minutes"),
        timedelta(minutes=15),
    )  # EU:15MIN
    THIRTY_MINUTES = "thirtyMinutes", _("Every thirty minute"), timedelta(minutes=30)  # EU:30MIN
    HOURLY = auto(), _("Every hour"), timedelta(hours=1)  # EU
    BIHOURLY = auto(), _("Every two hours"), timedelta(hours=2)  # EU
    TRIHOURLY = auto(), _("Every three hours"), timedelta(hours=3)  # EU
    TWELVE_HOURS = "twelveHours", _("Every twelve hours"), timedelta(hours=12)  # EU:12HRS
    SEVERAL_TIMES_A_DAY = "severalTimesADay", _("Several times a day"), timedelta(days=1)  # EU:CONT
    THREE_TIMES_A_DAY = "threeTimesADay", _("Three times a day"), timedelta(days=1)  # EU:DAILY_3
    SEMIDAILY = auto(), _("Twice a day"), timedelta(days=1)  # EU:DAILY_2
    DAILY = auto(), _("Daily"), timedelta(days=1)  # DC, EU
    FIVE_TIMES_A_WEEK = "fiveTimesAWeek", _("Five times a week"), timedelta(weeks=1)  # EU:WEEKLY_5
    THREE_TIMES_A_WEEK = (
        "threeTimesAWeek",
        _("Three times a week"),
        timedelta(weeks=1),
    )  # DC, EU:WEEKLY_3
    SEMIWEEKLY = auto(), _("Twice a week"), timedelta(weeks=1)  # DC, EU:WEEKLY_2
    WEEKLY = auto(), _("Weekly"), timedelta(weeks=1)  # DC, EU
    BIWEEKLY = auto(), _("Every two weeks"), timedelta(weeks=2)  # DC, EU
    THREE_TIMES_A_MONTH = (
        "threeTimesAMonth",
        _("Three times a month"),
        timedelta(days=31),
    )  # DC, EU:MONTHLY_3
    SEMIMONTHLY = auto(), _("Twice a month"), timedelta(days=31)  # DC, EU:MONTHLY_2
    MONTHLY = auto(), _("Monthly"), timedelta(days=31)  # DC, EU
    BIMONTHLY = auto(), _("Every two months"), timedelta(days=31 * 2)  # DC, EU
    QUARTERLY = auto(), _("Quarterly"), timedelta(days=31 * 3)  # DC, EU
    THREE_TIMES_A_YEAR = (
        "threeTimesAYear",
        _("Three times a year"),
        timedelta(days=365),
    )  # DC, EU:ANNUAL_3
    SEMIANNUAL = auto(), _("Twice a year"), timedelta(days=365)  # DC, EU:ANNUAL_2
    ANNUAL = auto(), _("Annually"), timedelta(days=365)  # DC, EU
    BIENNIAL = auto(), _("Every two years"), timedelta(days=365 * 2)  # DC, EU
    TRIENNIAL = auto(), _("Every three years"), timedelta(days=365 * 3)  # DC, EU
    QUADRENNIAL = auto(), _("Every four years"), timedelta(days=365 * 4)  # EU
    QUINQUENNIAL = auto(), _("Every five years"), timedelta(days=365 * 5)  # EU
    DECENNIAL = auto(), _("Every ten years"), timedelta(days=365 * 10)  # EU
    BIDECENNIAL = auto(), _("Every twenty years"), timedelta(days=365 * 20)  # EU
    TRIDECENNIAL = auto(), _("Every thirty years"), timedelta(days=365 * 30)  # EU
    PUNCTUAL = auto(), _("Punctual"), None  # EU:AS_NEEDED
    IRREGULAR = auto(), _("Irregular"), None  # DC, EU:IRREG
    NEVER = auto(), _("Never"), None  # EU
    NOT_PLANNED = "notPlanned", _("Not planned"), None  # EU:NOT_PLANNED
    OTHER = auto(), _("Other"), None  # EU
    UNKNOWN = auto(), _("Unknown"), None  # EU

    def __new__(cls, id: str, label: LazyString, delta: timedelta | None):
        # Set _value_ so the enum value-based lookup depends only on the id field.
        # See https://docs.python.org/3/howto/enum.html#when-to-use-new-vs-init
        obj = str.__new__(cls, id)
        obj._value_ = id
        obj._label = label  # type: ignore[misc]
        obj._delta = delta  # type: ignore[misc]
        return obj

    @classmethod
    def _missing_(cls, value) -> "UpdateFrequency | None":
        if isinstance(value, str):
            return UpdateFrequency._LEGACY_FREQUENCIES.get(value)  # type: ignore[misc]

    @property
    def id(self) -> str:
        return self.value

    @property
    def label(self) -> LazyString:
        return self._label  # type: ignore[misc]

    @property
    def delta(self) -> timedelta | None:
        return self._delta  # type: ignore[misc]

    def next_update(self, last_update: datetime) -> datetime | None:
        return last_update + self.delta if self.delta else None


# We must declare UpdateFrequency class variables after the Enum magic
# happens, so outside of class declaration.
#
# The alternative method based on _ignore_ breaks accessing the class
# variables from outside the class, because accesses to will go
# through __getattr__ as if it were an Enum entry.
#
# FIXME(python 3.13+): Use Enum._add_value_alias_ instead:
#
#     UNKNOWN = auto(), _("Unknown"), None, []
#     CONTINUOUS = auto(), _("Real time"), None, ["realtime"]
#     SEVERAL_TIMES_A_DAY = "severalTimesADay", ..., ["fourTimesADay"]
#
#     def __new__(cls, id: str, ..., aliases: list[str]):
#         ...
#         for alias in aliases:
#             obj._add_value_alias_(alias)
#
UpdateFrequency._LEGACY_FREQUENCIES = {  # type: ignore[misc]
    "realtime": UpdateFrequency.CONTINUOUS,
    "fourTimesADay": UpdateFrequency.SEVERAL_TIMES_A_DAY,
    "fourTimesAWeek": UpdateFrequency.OTHER,
    "fortnighly": UpdateFrequency.BIWEEKLY,
    "biannual": UpdateFrequency.SEMIANNUAL,
}


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
SPD = "spd"
INSPIRE = "inspire"
HVD = "hvd"
SL = "sl"
SR = "sr"
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
