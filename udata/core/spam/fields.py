from udata.api import api, fields

from .constants import SPAM_STATUS_CHOICES

spam_fields = api.model(
    "Spam",
    {
        "status": fields.String(description="Status", enum=SPAM_STATUS_CHOICES, readonly=True),
    },
)

potential_spam_fields = api.model(
    "PotentialSpam",
    {
        "message": fields.String(readonly=True),
    },
)
