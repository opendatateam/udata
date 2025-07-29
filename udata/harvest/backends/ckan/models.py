from udata.api import fields
from udata.core.dataset.api_fields import dataset_harvest_fields

# Register additional harvest fields to serve by api
dataset_harvest_fields["ckan_name"] = fields.String(
    description="The ckan name property for ckan harvested dataset", allow_null=True
)
dataset_harvest_fields["ckan_source"] = fields.String(
    description="The ckan source property for ckan harvested dataset", allow_null=True
)
