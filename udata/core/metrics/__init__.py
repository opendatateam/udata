def init_app(app):
    # Load all core metrics
    import udata.core.user.metrics  # noqa
    import udata.core.organization.metrics
    import udata.core.discussions.metrics
    import udata.core.dataset.metrics
    import udata.core.dataservices.metrics
    import udata.core.reuse.metrics
    import udata.core.followers.metrics  # noqa
