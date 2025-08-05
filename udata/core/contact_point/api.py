from udata.api import API, api
from udata.api.parsers import ModelApiParser
from udata.core.dataset.permissions import OwnablePermission
from udata.forms import validators
from udata.i18n import lazy_gettext as _

from .api_fields import contact_point_fields, contact_point_roles_fields
from .forms import ContactPointForm
from .models import CONTACT_ROLES, ContactPoint


class ContactPointApiParser(ModelApiParser):
    sorts = {}

    def __init__(self):
        super().__init__()


ns = api.namespace("contacts", "Contact points related operations")

contact_point_parser = ContactPointApiParser()


@ns.route("/", endpoint="contact_points")
class ContactPointsListAPI(API):
    """Contact points collection endpoint"""

    @api.secure
    @api.doc("create_contact_point")
    @api.expect(contact_point_fields)
    @api.marshal_with(contact_point_fields)
    @api.response(400, "Validation error")
    def post(self):
        """Creates a contact point"""
        form = api.validate(ContactPointForm)
        contact_point, created = ContactPoint.objects.get_or_create(**form.data)

        return contact_point, 201 if created else 200


@ns.route("/<contact_point:contact_point>/", endpoint="contact_point")
@api.response(404, "Contact point not found")
class ContactPointAPI(API):
    @api.doc("get_contact_point")
    @api.marshal_with(contact_point_fields)
    def get(self, contact_point):
        """Get a contact point given its identifier"""
        return contact_point

    @api.secure
    @api.doc("update_contact_point")
    @api.expect(contact_point_fields)
    @api.marshal_with(contact_point_fields)
    @api.response(400, "Validation error")
    def put(self, contact_point):
        """Updates a contact point given its identifier"""
        OwnablePermission(contact_point).test()

        form = api.validate(ContactPointForm, contact_point)
        if ContactPoint.objects().filter(**form.data).count():
            raise validators.ValidationError(
                _("An existing contact point already exists with these informations.")
            )

        return form.save()

    @api.secure
    @api.doc("delete_contact_point")
    @api.response(204, "Contact point deleted")
    def delete(self, contact_point):
        """Deletes a contact point given its identifier"""
        OwnablePermission(contact_point).test()

        contact_point.delete()
        return "", 204


@ns.route("/roles/", endpoint="contact_point_roles")
class ContactPointRolesAPI(API):
    """Contact point roles endpoint"""

    @api.doc("contact_point_roles")
    @api.marshal_list_with(contact_point_roles_fields)
    def get(self):
        """List all contact point roles"""
        return [{"id": id, "label": label} for id, label in CONTACT_ROLES.items()]
