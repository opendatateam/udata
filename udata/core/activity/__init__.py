import logging

log = logging.getLogger(__name__)


def init_app(app):
    # Load all core actvitiess
    import udata.core.user.activities  # noqa
    import udata.core.dataservices.activities  # noqa
    import udata.core.dataset.activities  # noqa
    import udata.core.reuse.activities  # noqa
    import udata.core.organization.activities  # noqa
