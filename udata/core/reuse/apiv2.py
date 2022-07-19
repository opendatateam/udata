from flask import abort, jsonify

from webargs import fields as arg_field, validate as arg_validate
from webargs.flaskparser import use_args

from udata import search
from udata.app import Blueprint
from udata.api.fields import paginate_schema

from .models import Reuse
from .apiv2_schemas import ReuseSchema


ns = Blueprint('reuses', __name__)

DEFAULT_SORTING = '-created_at'


SORTS = [
    'created',
    'datasets',
    'followers',
    'views',
    '-created',
    '-datasets',
    '-followers',
    '-views'
]


reuse_search_args = {
    "q": arg_field.Str(),
    'badge': arg_field.Str(),
    'tag': arg_field.Str(),
    'organization': arg_field.Str(),
    'owner': arg_field.Str(),
    'featured': arg_field.Bool(),
    'type': arg_field.Str(),
    'topic': arg_field.Str(),
    'sort': arg_field.Str(validate=arg_validate.OneOf(SORTS)),
    'page': arg_field.Int(missing=1),
    'page_size': arg_field.Int(missing=20)
}


@ns.route('/search/', endpoint='reuse_search', methods=['GET'])
@use_args(reuse_search_args, location="query")
def get_reuse_search(args):
    '''Reuses collection search endpoint'''
    try:
        result = search.query(Reuse, **args)
        schema = paginate_schema(ReuseSchema)
        return jsonify(schema().dump(result))
    except NotImplementedError:
        abort(501, 'Search endpoint not enabled')
    except RuntimeError:
        abort(500, 'Internal search service error')
