from flask_restx.inputs import boolean
from mongoengine import NULLIFY

from udata.api_fields import field, generate_fields
from udata.core.organization.notifications import MembershipRequestNotificationDetails
from udata.core.user.api_fields import user_ref_fields
from udata.core.user.models import User
from udata.models import db
from udata.mongo.datetime_fields import Datetimed
from udata.mongo.queryset import UDataQuerySet


class NotificationQuerySet(UDataQuerySet):
    def with_organization_in_details(self, organization):
        """This function must be updated to handle new details cases"""
        return self(details__request_organization=organization)

    def with_user_in_details(self, user):
        """This function must be updated to handle new details cases"""
        return self(details__request_user=user)


def is_handled(base_query, filter_value):
    if filter_value is None:
        return base_query
    if filter_value is True:
        return base_query.filter(handled_at__ne=None)
    return base_query.filter(handled_at=None)


@generate_fields()
class Notification(Datetimed, db.Document):
    meta = {
        "ordering": ["-created_at"],
        "queryset_class": NotificationQuerySet,
    }

    id = field(db.AutoUUIDField(primary_key=True))
    handled_at = field(
        db.DateTimeField(),
        sortable=True,
        auditable=False,
        filterable={"key": "handled", "query": is_handled, "type": boolean},
    )
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
