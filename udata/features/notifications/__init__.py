import logging

log = logging.getLogger(__name__)


def init_app(app):
    # Load core notifications
    import udata.core.organization.notifications  # noqa
    import udata.core.discussions.notifications
    import udata.harvest.notifications

    # Load feature notifications
    import udata.features.transfer.notifications

    # Following what one works on
    import udata.features.notifications.follow  # noqa
