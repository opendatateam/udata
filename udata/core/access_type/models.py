from udata.api_fields import field, generate_fields
from udata.core.access_type.constants import (
    AccessAudienceCondition,
    AccessAudienceType,
    AccessType,
    InspireLimitationCategory,
)
from udata.i18n import lazy_gettext as _
from udata.models import db
from udata.mongo.errors import FieldValidationError


@generate_fields()
class AccessAudience(db.EmbeddedDocument):
    role = field(db.StringField(choices=[e.value for e in AccessAudienceType]), filterable={})
    condition = field(
        db.StringField(choices=[e.value for e in AccessAudienceCondition]), filterable={}
    )


def check_only_one_condition_per_role(access_audiences, **_kwargs):
    roles = set(e["role"] for e in access_audiences)
    if len(roles) != len(access_audiences):
        raise FieldValidationError(
            _("You can only set one condition for a given access audience role"),
            field="access_audiences",
        )


class WithAccessType:
    access_type = field(
        db.EnumField(AccessType, default=AccessType.OPEN),
        filterable={},
    )
    access_audiences = field(
        db.EmbeddedDocumentListField(AccessAudience),
        checks=[check_only_one_condition_per_role],
    )

    authorization_request_url = field(db.URLField())
    access_type_reason_category = field(
        db.StringField(choices=[e.value for e in InspireLimitationCategory]), allow_null=True
    )
    access_type_reason = field(db.StringField())
