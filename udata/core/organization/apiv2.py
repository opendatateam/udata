from flask import abort, jsonify

from webargs import fields as arg_field, validate as arg_validate
from webargs.flaskparser import use_args

from udata import search
from udata.app import Blueprint
from udata.api.fields import paginate_schema
from .models import Organization
from .apiv2_schemas import OrganizationSchema


ns = Blueprint('organizations', __name__)


SORTS = [
    'reuses',
    'datasets',
    'followers',
    'views',
    'created',
    '-reuses',
    '-datasets',
    '-followers',
    '-views',
    '-created'
]


organization_search_args = {
    "q": arg_field.Str(),
    'badge': arg_field.Str(),
    'sort': arg_field.Str(validate=arg_validate.OneOf(SORTS)),
    'page': arg_field.Int(missing=1),
    'page_size': arg_field.Int(missing=20)
}


DEFAULT_SORTING = '-created_at'


@ns.route('/search/', endpoint='organization_search', methods=['GET'])
@use_args(organization_search_args, location="query")
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
