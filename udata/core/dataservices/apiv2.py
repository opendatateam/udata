from udata import search
from udata.api import API, apiv2, fields
from udata.core.access_type.models import AccessAudience
from udata.core.dataservices.models import Dataservice, HarvestMetadata

from .models import dataservice_permissions_fields
from .search import DataserviceSearch

apiv2.inherit("DataservicePermissions", dataservice_permissions_fields)
apiv2.inherit("DataservicePage", Dataservice.__page_fields__)
apiv2.inherit("Dataservice (read)", Dataservice.__read_fields__)
apiv2.inherit("DataserviceReference", Dataservice.__ref_fields__)
apiv2.inherit("HarvestMetadata (read)", HarvestMetadata.__read_fields__)
apiv2.inherit("AccessAudience (read)", AccessAudience.__read_fields__)
dataservice_search_page_fields = apiv2.model(
    "DataserviceSearchPage", fields.search_pager(Dataservice.__read_fields__)
)

ns = apiv2.namespace("dataservices", "Dataservice related operations")

search_parser = DataserviceSearch.as_request_parser(store_missing=False)


@ns.route("/search/", endpoint="dataservice_search")
class DataserviceSearchAPI(API):
    """Dataservices collection search endpoint"""

    @apiv2.doc("search_dataservices")
    @apiv2.expect(search_parser)
    @apiv2.marshal_with(dataservice_search_page_fields)
    def get(self):
        """Search all dataservices"""
        args = search_parser.parse_args()
        return search.query(DataserviceSearch, **args)
