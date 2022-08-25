from flask import abort

from flask_apispec import use_kwargs, marshal_with

from udata import search
from udata.api import apiv2_blueprint as apiv2
from .models import Organization
from .apiv2_schemas import OrganizationPaginationSchema
from .search import OrganizationSearch


search_arguments = OrganizationSearch.as_request_parser()


DEFAULT_SORTING = '-created_at'


@apiv2.route('/organizations/search/', endpoint='organization_search', methods=['GET'])
@use_kwargs(search_arguments, location="query")
@marshal_with(OrganizationPaginationSchema())
def get_organization_search(**kwargs):
    """Organizations collection search endpoint."""
    try:
        return search.query(Organization, **kwargs)
    except NotImplementedError:
        abort(501, 'Search endpoint not enabled')
    except RuntimeError:
        abort(500, 'Internal search service error')
