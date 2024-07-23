from udata.core.dataservices.models import Dataservice
from udata.core.dataset.models import Dataset
from udata.core.discussions.models import Discussion
from udata.core.organization.models import Organization
from udata.core.reuse.models import Reuse
from udata.i18n import lazy_gettext as _

REASON_PERSONAL_DATA = "personal_data"
REASON_EXPLICIT_CONTENT = "explicit_content"
REASON_ILLEGAL_CONTENT = "illegal_content"
REASON_OTHERS = "others"
REASON_SECURITY = "security"
REASON_SPAM = "spam"


def reports_reasons_translations() -> list:
    """
    This is a function to avoid creating the list with a wrong lang
    at the start of the app.
    """
    return [
        {"value": REASON_EXPLICIT_CONTENT, "label": _("Explicit content")},
        {"value": REASON_ILLEGAL_CONTENT, "label": _("Illegal content")},
        {"value": REASON_OTHERS, "label": _("Others")},
        {"value": REASON_PERSONAL_DATA, "label": _("Personal data")},
        {"value": REASON_SECURITY, "label": _("Security")},
        {"value": REASON_SPAM, "label": _("Spam")},
    ]


REPORT_REASONS_CHOICES: list[str] = [item["value"] for item in reports_reasons_translations()]
REPORTABLE_MODELS = [Dataset, Reuse, Discussion, Organization, Dataservice]
