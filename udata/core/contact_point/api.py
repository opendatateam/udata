from flask import request
from flask_login import current_user

from udata.api import API, api, fields
from udata.api_fields import patch
from udata.core.dataset.permissions import OwnablePermission
from udata.i18n import lazy_gettext as _
from udata.mongo.errors import FieldValidationError

from .models import CONTACT_ROLES, ContactPoint

ns = api.namespace("contacts", "Contact points related operations")


@ns.route("/", endpoint="contact_points")
class ContactPointsListAPI(API):
    """Contact points collection endpoint"""

    @api.secure
    @api.doc("create_contact_point")
    @api.expect(ContactPoint.__write_fields__)
    @api.marshal_with(ContactPoint.__read_fields__)
    @api.response(400, "Validation error")
    def post(self):
        """Creates a contact point"""
        contact_point = patch(ContactPoint(), request)
        if not contact_point.owner and not contact_point.organization:
            contact_point.owner = current_user._get_current_object()
        query = {
            "name": contact_point.name,
            "email": contact_point.email,
            "contact_form": contact_point.contact_form,
            "role": contact_point.role,
            "owner": contact_point.owner,
            "organization": contact_point.organization,
        }
        existing = ContactPoint.objects(**query).first()
        if existing:
            return existing, 200

        contact_point.save()
        return contact_point, 201


@ns.route("/<contact_point:contact_point>/", endpoint="contact_point")
@api.response(404, "Contact point not found")
class ContactPointAPI(API):
    @api.doc("get_contact_point")
    @api.marshal_with(ContactPoint.__read_fields__)
    def get(self, contact_point):
        """Get a contact point given its identifier"""
        return contact_point

    @api.secure
    @api.doc("update_contact_point")
    @api.expect(ContactPoint.__write_fields__)
    @api.marshal_with(ContactPoint.__read_fields__)
    @api.response(400, "Validation error")
    def put(self, contact_point):
        """Updates a contact point given its identifier"""
        OwnablePermission(contact_point).test()

        contact_point = patch(contact_point, request)
        query = {
            "name": contact_point.name,
            "email": contact_point.email,
            "contact_form": contact_point.contact_form,
            "role": contact_point.role,
            "owner": contact_point.owner,
            "organization": contact_point.organization,
        }
        if ContactPoint.objects(**query).filter(id__ne=contact_point.id).count():
            raise FieldValidationError(
                _("An existing contact point already exists with these informations."),
                field="name",
            )

        contact_point.save()
        return contact_point

    @api.secure
    @api.doc("delete_contact_point")
    @api.response(204, "Contact point deleted")
    def delete(self, contact_point):
        """Deletes a contact point given its identifier"""
        OwnablePermission(contact_point).test()

        contact_point.delete()
        return "", 204


contact_point_roles_fields = api.model(
    "ContactPointRoles",
    {
        "id": fields.String(description="The contact role identifier"),
        "label": fields.String(description="The contact role display name"),
    },
)


@ns.route("/roles/", endpoint="contact_point_roles")
class ContactPointRolesAPI(API):
    """Contact point roles endpoint"""

    @api.doc("contact_point_roles")
    @api.marshal_list_with(contact_point_roles_fields)
    def get(self):
        """List all contact point roles"""
        return [{"id": id, "label": label} for id, label in CONTACT_ROLES.items()]
