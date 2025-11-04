from mongoengine import NULLIFY

from udata.api_fields import field, generate_fields
from udata.core.organization.notifications import MembershipRequestNotificationDetails
from udata.core.user.api_fields import user_ref_fields
from udata.core.user.models import User
from udata.models import db
from udata.mongo.datetime_fields import Datetimed


@generate_fields()
class Notification(Datetimed, db.Document):
    # meta = {"allow_inheritance": True}

    id = field(db.AutoUUIDField(primary_key=True))
    user = field(
        db.ReferenceField(User, reverse_delete_rule=NULLIFY),
        nested_fields=user_ref_fields,
        readonly=True,
        allow_null=True,
        auditable=False,
        filterable={},
    )
    details = field(
        db.GenericEmbeddedDocumentField(choices=(MembershipRequestNotificationDetails,)),
        generic=True,
    )
