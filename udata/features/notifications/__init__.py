import logging
from importlib import import_module

log = logging.getLogger(__name__)


def init_app(app):
    # Importing a module connects its notification handlers
    for module in (
        # Core notifications
        "udata.core.organization.notifications",
        "udata.core.discussions.notifications",
        "udata.harvest.notifications",
        # Feature notifications
        "udata.features.transfer.notifications",
        # Following what one works on
        "udata.features.notifications.follow",
    ):
        import_module(module)
