from flask import Blueprint

from udata.api import API, api
from udata.core.access_type.utils import get_inspire_limitation_labels

blueprint = Blueprint("access_type", __name__, url_prefix="/api/1/access_type")
ns = api.namespace("access_type", "Access type related operations")


@ns.route("/reason_categories/", endpoint="reason_categories")
class ReasonCategoriesAPI(API):
    @api.doc("reason_categories")
    def get(self):
        """List all INSPIRE limitation reason categories"""
        return [
            {"value": value, "label": label}
            for value, label in get_inspire_limitation_labels().items()
        ]
