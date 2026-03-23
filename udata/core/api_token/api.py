from udata.api import api, fields

from .models import ApiToken

apitoken_created_fields = api.inherit(
    "ApiTokenCreated",
    ApiToken.__read_fields__,
    {
        "token": fields.String(
            attribute="_plaintext",
            readonly=True,
            description="The plaintext token (shown only once at creation)",
        ),
    },
)
