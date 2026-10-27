import logging
from importlib import import_module

log = logging.getLogger(__name__)


def init_app(app):
    # Load all core activities: importing a module registers its activities
    for module in (
        "udata.core.user.activities",
        "udata.core.dataservices.activities",
        "udata.core.dataset.activities",
        "udata.core.reuse.activities",
        "udata.core.organization.activities",
        "udata.core.topic.activities",
    ):
        import_module(module)
