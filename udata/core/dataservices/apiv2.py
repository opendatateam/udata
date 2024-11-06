from flask import request

from udata import search
from udata.api import API, apiv2
from udata.core.dataservices.models import Dataservice, HarvestMetadata
from udata.utils import multi_to_dict

from .search import DataserviceSearch

apiv2.inherit("DataservicePage", Dataservice.__page_fields__)
apiv2.inherit("Dataservice (read)", Dataservice.__read_fields__)
apiv2.inherit("HarvestMetadata (read)", HarvestMetadata.__read_fields__)

ns = apiv2.namespace("dataservices", "Dataservice related operations")

search_parser = DataserviceSearch.as_request_parser()


@ns.route("/search/", endpoint="dataservice_search")
class DataserviceSearchAPI(API):
    """Dataservices collection search endpoint"""

    @apiv2.doc("search_dataservices")
    @apiv2.expect(search_parser)
    @apiv2.marshal_with(Dataservice.__page_fields__)
    def get(self):
        """Search all dataservices"""
        search_parser.parse_args()
        return search.query(DataserviceSearch, **multi_to_dict(request.args))
