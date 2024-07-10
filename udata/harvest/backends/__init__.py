from udata.entrypoints import EntrypointError, get_enabled


def get(app, name):
    """Get a backend given its name"""
    backend = get_all(app).get(name)
    if not backend:
        msg = 'Harvest backend "{0}" is not registered'.format(name)
        raise EntrypointError(msg)
    return backend


def get_all(app):
    return get_enabled("udata.harvesters", app)


from .base import BaseBackend, HarvestFeature, HarvestFilter  # noqa
