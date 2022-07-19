from flask import abort, jsonify

from webargs.flaskparser import use_args

from udata import search
from udata.app import Blueprint
from udata.api.fields import paginate_schema

from .models import Reuse
from .apiv2_schemas import ReuseSchema
from .search import ReuseSearch


ns = Blueprint('reuses', __name__)
search_arguments = ReuseSearch.as_request_parser()

DEFAULT_SORTING = '-created_at'


@ns.route('/search/', endpoint='reuse_search', methods=['GET'])
@use_args(search_arguments, location="query")
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
