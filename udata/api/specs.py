from apispec import APISpec
from apispec.ext.marshmallow import MarshmallowPlugin
from apispec_webframeworks.flask import FlaskPlugin
from flask_apispec.extension import FlaskApiSpec

from udata.core.dataset.apiv2 import get_dataset_search, get_resources_paginated, get_specific_dataset_by_id, get_specific_resource_by_rid
from udata.core.organization.apiv2 import get_organization_search
from udata.core.reuse.apiv2 import get_reuse_search


def init_app(app):
    app.config.update({
        'APISPEC_SPEC': APISpec(
            title="Udata",
            version="1.0.0",
            openapi_version="3.0.2",
            plugins=[FlaskPlugin(), MarshmallowPlugin()],
        ),
        'APISPEC_SWAGGER_URL': '/swagger/',
    })

    docs = FlaskApiSpec(app)
    with app.app_context():
        docs.register(get_dataset_search, endpoint='apiv2.dataset_search')
