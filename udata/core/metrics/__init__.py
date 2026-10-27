from importlib import import_module


def init_app(app):
    # Load all core metrics: importing a module connects its signal handlers
    for module in (
        "udata.core.user.metrics",
        "udata.core.organization.metrics",
        "udata.core.discussions.metrics",
        "udata.core.dataset.metrics",
        "udata.core.dataservices.metrics",
        "udata.core.reuse.metrics",
        "udata.core.followers.metrics",
    ):
        import_module(module)
