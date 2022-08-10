from flask import abort, jsonify

from webargs.flaskparser import use_args

from udata import search
from udata.api import apiv2_blueprint as apiv2
from .models import Organization
from .apiv2_schemas import OrganizationPaginationSchema
from .search import OrganizationSearch


search_arguments = OrganizationSearch.as_request_parser()


DEFAULT_SORTING = '-created_at'


@apiv2.route('/organizations/search/', endpoint='organization_search', methods=['GET'])
@use_args(search_arguments, location="query")
def get_organization_search(args):
    """Organizations collection search endpoint.
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
          enum: [created, reuses, datasets, followers, views]
      - in: query
        name: badge
        schema:
          type: string
      responses:
        200:
          content:
            application/json:
              schema: OrganizationPaginationSchema
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
        result = search.query(Organization, **args)
        return jsonify(OrganizationPaginationSchema().dump(result))
    except NotImplementedError:
        abort(501, 'Search endpoint not enabled')
    except RuntimeError:
        abort(500, 'Internal search service error')
