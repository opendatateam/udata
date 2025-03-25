from udata.api import api, fields

badge_fields = api.model(
    "Badge",
    {
        "kind": fields.String(
            description=("Kind of badge (certified, etc), specific to each model"), required=True
        ),
    },
)
