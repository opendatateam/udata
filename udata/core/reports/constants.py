
from udata.core.dataset.models import Dataset
from udata.i18n import lazy_gettext as _


REASON_SPAM = 'spam'
REASON_PERSONAL_DATA = 'personal_data'
REASON_EXPLICIT_CONTENT = 'explicit_content'
REASON_ILLEGAL_CONTENT = 'illegal_content'
REASON_SECURITY = 'security'
REASON_OTHERS = 'others'

def reports_reasons_translations():
    '''
    This is a function to avoid creating the dict with a wrong lang
    at the start of the app.
    '''
    return {
        REASON_SPAM: _('Spam'),
        REASON_PERSONAL_DATA: _('Personal data'),
        REASON_EXPLICIT_CONTENT: _('Explicit content'),
        REASON_ILLEGAL_CONTENT: _('Illegal content'),
        REASON_SECURITY: _('Security'),
        REASON_OTHERS: _('Others'),
    }

REPORT_REASONS_CHOICES = [key for key, _ in reports_reasons_translations().items()]
REPORTABLE_MODELS = [Dataset]