import logging

from . import (
    models,  # noqa: F401 (registers the GeopfToken document)
    tasks,  # noqa: F401 (registers Celery tasks)
)

log = logging.getLogger(__name__)


def init_app(app):
    log.info("geopf: plugin init_app called")
