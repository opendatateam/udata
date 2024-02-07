from udata.api import api, fields
from .models import SPAM_STATUS_CHOICES

spam_fields = api.model('Spam', {
    'status': fields.String(description='Status', enum=SPAM_STATUS_CHOICES, readonly=True),
})
