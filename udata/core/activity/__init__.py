import logging

log = logging.getLogger(__name__)


def init_app(app):
    # Load all core actvitiess
    import udata.core.user.activities  # noqa
    import udata.core.dataservices.activities
    import udata.core.dataset.activities
    import udata.core.reuse.activities
    import udata.core.organization.activities
    import udata.core.topic.activities  # noqa
