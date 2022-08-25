from flask import abort

from flask_apispec import use_kwargs, marshal_with

from udata import search
from udata.api import apiv2_blueprint as apiv2

from .models import Reuse
from .apiv2_schemas import ReusePaginationSchema
from .search import ReuseSearch


search_arguments = ReuseSearch.as_request_parser()

DEFAULT_SORTING = '-created_at'


@apiv2.route('/reuses/search/', endpoint='reuse_search', methods=['GET'])
@use_kwargs(search_arguments, location="query")
@marshal_with(ReusePaginationSchema())
def get_reuse_search(**kwargs):
    """Reuses collection search endpoint."""
    try:
        return search.query(Reuse, **kwargs)
    except NotImplementedError:
        abort(501, 'Search endpoint not enabled')
    except RuntimeError:
        abort(500, 'Internal search service error')
