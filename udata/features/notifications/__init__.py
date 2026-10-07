import logging

log = logging.getLogger(__name__)


def init_app(app):
    # Load core notifications
    import udata.core.organization.notifications  # noqa
    import udata.core.discussions.notifications  # noqa
    import udata.harvest.notifications  # noqa

    # Load feature notifications
    import udata.features.transfer.notifications  # noqa

    # Following what one works on
    from udata.features.notifications.follow import add_followed_header

    app.after_request(add_followed_header)
