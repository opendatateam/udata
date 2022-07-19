from flask import abort, jsonify

from webargs.flaskparser import use_args

from udata import search
from udata.app import Blueprint
from udata.api.fields import paginate_schema
from .models import Organization
from .apiv2_schemas import OrganizationSchema
from .search import OrganizationSearch


ns = Blueprint('organizations', __name__)


search_arguments = OrganizationSearch.as_request_parser()


DEFAULT_SORTING = '-created_at'


@ns.route('/search/', endpoint='organization_search', methods=['GET'])
@use_args(search_arguments, location="query")
def get_organization_search(args):
    '''Organizations collection search endpoint'''
    try:
        result = search.query(Organization, **args)
        schema = paginate_schema(OrganizationSchema)
        return jsonify(schema().dump(result))
    except NotImplementedError:
        abort(501, 'Search endpoint not enabled')
    except RuntimeError:
        abort(500, 'Internal search service error')
