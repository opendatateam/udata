from flask import abort, jsonify

from webargs.flaskparser import use_args

from udata import search
from udata.api import apiv2_blueprint as apiv2

from .models import Reuse
from .apiv2_schemas import ReusePaginationSchema
from .search import ReuseSearch


search_arguments = ReuseSearch.as_request_parser()

DEFAULT_SORTING = '-created_at'


@apiv2.route('/reuses/search/', endpoint='reuse_search', methods=['GET'])
@use_args(search_arguments, location="query")
def get_reuse_search(args):
    """Reuses collection search endpoint.
    ---
    get:
      parameters:
      - in: query
        name: q
        required: true
        schema:
          type: string
      - in: query
        name: page
        schema:
          type: integer
          default: 1
      - in: query
        name: page_size
        schema:
          type: integer
          default: 20
      - in: query
        name: sort
        schema:
          type: string
          enum: [created, datasets, followers, views]
      - in: query
        name: tag
        schema:
          type: string
      - in: query
        name: organization
        schema:
          type: string
      - in: query
        name: owner
        schema:
          type: string
      - in: query
        name: type
        schema:
          type: string
      - in: query
        name: badge
        schema:
          type: string
      - in: query
        name: featured
        schema:
          type: boolean
      - in: query
        name: topic
        schema:
          type: string
      responses:
        200:
          content:
            application/json:
              schema: ReusePaginationSchema
        500:
          content:
            text/plain:
              schema:
                type: string
        501:
          content:
            text/plain:
              schema:
                type: string
    """
    try:
        result = search.query(Reuse, **args)
        return jsonify(ReusePaginationSchema().dump(result))
    except NotImplementedError:
        abort(501, 'Search endpoint not enabled')
    except RuntimeError:
        abort(500, 'Internal search service error')
