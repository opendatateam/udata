from apispec import APISpec
from apispec.ext.marshmallow import MarshmallowPlugin
from flask_apispec.extension import FlaskApiSpec


def init_app(app):
    app.config.update({
        'APISPEC_SPEC': APISpec(
            title="udata",
            version="2.0.0",
            openapi_version="3.0.2",
            plugins=[MarshmallowPlugin()],
        ),
        'APISPEC_SWAGGER_URL': '/api/2/swagger/',
        'APISPEC_SWAGGER_UI_URL': None
    })

    docs = FlaskApiSpec(app)
    with app.app_context():
        for (fpath, view_function) in app.view_functions.items():
            api_version = fpath.split('.')[0]
            if api_version == 'apiv2':
                docs.register(view_function, endpoint=fpath)
