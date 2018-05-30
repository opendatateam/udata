from importlib import import_module

import logging

log = logging.getLogger(__name__)


def init_app(app):
    # Load core notifications
    import udata.core.organization.notifications  # noqa
    import udata.core.discussions.notifications  # noqa
    import udata.core.issues.notifications  # noqa
    import udata.harvest.notifications  # noqa

    # Load feature notifications
    import udata.features.transfer.notifications  # noqa
