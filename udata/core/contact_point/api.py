import mongoengine

from udata.api import API, api
from udata.api.parsers import ModelApiParser

from .api_fields import contact_point_fields
from .forms import ContactPointForm


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
        try:
            contact_point = form.save()
        except mongoengine.errors.ValidationError as e:
            api.abort(400, e.message)
        return contact_point, 201


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
        form = api.validate(ContactPointForm, contact_point)
        return form.save()

    @api.secure
    @api.doc("delete_contact_point")
    @api.response(204, "Contact point deleted")
    def delete(self, contact_point):
        """Deletes a contact point given its identifier"""
        contact_point.delete()
        return "", 204
