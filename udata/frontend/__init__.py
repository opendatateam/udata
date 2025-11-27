import logging

from .markdown import init_app as init_markdown

log = logging.getLogger(__name__)


def init_app(app):
    from udata.core.storages.views import blueprint as storage_blueprint

    init_markdown(app)

    app.register_blueprint(storage_blueprint)
