from apispec import APISpec
from apispec.ext.marshmallow import MarshmallowPlugin
from apispec_webframeworks.flask import FlaskPlugin

from udata.api import apiv2_blueprint as apiv2
from udata.core.dataset.apiv2 import get_dataset_search, get_resources_paginated, get_specific_dataset_by_id, get_specific_resource_by_rid
from udata.core.organization.apiv2 import get_organization_search
from udata.core.reuse.apiv2 import get_reuse_search


spec = APISpec(
    title="Udata",
    version="1.0.0",
    openapi_version="3.0.2",
    info=dict(description="Udata API specs"),
    plugins=[FlaskPlugin(), MarshmallowPlugin()],
)


@apiv2.route('/apidoc/', methods=['GET'])
def get_api_doc():
    spec.path(view=get_dataset_search)
    spec.path(view=get_resources_paginated)
    spec.path(view=get_specific_dataset_by_id)
    spec.path(view=get_specific_resource_by_rid)
    spec.path(view=get_organization_search)
    spec.path(view=get_reuse_search)
    return spec.to_dict()
