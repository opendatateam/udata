from udata.api import api, API
from udata.api.parsers import ModelApiParser

from .api_fields import contact_points_fields, contact_points_page_fields
from .forms import ContactPointForm
from .models import ContactPoint


class ContactPointApiParser(ModelApiParser):
    sorts = {}

    def __init__(self):
        super().__init__()

    @staticmethod
    def parse_filters(contact_points, args):
        if args.get('q'):
            # Following code splits the 'q' argument by spaces to surround
            # every word in it with quotes before rebuild it.
            # This allows the search_text method to tokenise with an AND
            # between tokens whereas an OR is used without it.
            phrase_query = ' '.join([f'"{elem}"' for elem in args['q'].split(' ')])
            contact_points = contact_points.search_text(phrase_query)
        return contact_points


ns = api.namespace('contact_points', 'Contact points related operations')

contact_point_parser = ContactPointApiParser()


@ns.route('/', endpoint='contact_points')
class ContactPointsListAPI(API):
    '''Contact points collection endpoint'''

    @api.doc('list_contact_points')
    @api.marshal_with(contact_points_page_fields)
    def get(self):
        '''List all contact points'''
        args = contact_point_parser.parse()
        return ContactPoint.objects().paginate(args['page'], args['page_size'])


@ns.route('/<contact_point:contact_point>/', endpoint='contact_point')
@api.response(404, 'Contact point not found')
class ContactPointAPI(API):
    @api.secure
    @api.doc('update_contact_point')
    @api.expect(contact_points_fields)
    @api.marshal_with(contact_points_fields)
    @api.response(400, 'Validation error')
    def put(self, contact_point):
        '''Updates a contact point given its identifier'''
        form = api.validate(ContactPointForm, contact_point)
        return form.save()

    @api.secure
    @api.doc('delete_contact_point')
    @api.response(204, 'Contact point deleted')
    def delete(self, contact_point):
        '''Deletes a contact point given its identifier'''
        contact_point.delete()
        return '', 204