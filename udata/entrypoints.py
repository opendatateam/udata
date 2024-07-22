import pkg_resources

# Here for documentation purpose
ENTRYPOINTS = {
    "udata.avatars": "Avatar rendering backends",
    "udata.harvesters": "Harvest backends",
    "udata.linkcheckers": "Link checker backends",
    "udata.metrics": "Extra metrics",
    "udata.models": "Models and migrations",
    "udata.preview": "Displays preview for resources",
    "udata.plugins": "Generic plugin",
    "udata.tasks": "Tasks and jobs",
    "udata.themes": "Themes",
    "udata.views": "Extra views",
}


class EntrypointError(Exception):
    pass


def iter_all(name):
    """Iter all entrypoints registered on a given key"""
    return pkg_resources.iter_entry_points(name)


def get_all(entrypoint_key):
    """Load all entrypoints registered on a given key"""
    return dict(_ep_to_kv(e) for e in iter_all(entrypoint_key))


def get_enabled(name, app):
    """
    Get (and load) entrypoints registered on name
    and enabled for the given app.
    """
    plugins = app.config["PLUGINS"]
    return dict(
        _ep_to_kv(e)
        for e in iter_all(name)
        if e.name in plugins or e.name.startswith(tuple(plugins))
    )


def get_plugin_module(name, app, plugin):
    """
    Get the module for a given plugin
    """
    return next((m for p, m in get_enabled(name, app).items() if p == plugin), None)


def _ep_to_kv(entrypoint):
    """
    Transform an entrypoint into a key-value tuple where:
    - key is the entrypoint name
    - value is the entrypoint class with the name attribute
      matching from entrypoint name
    """
    cls = entrypoint.load()
    cls.name = entrypoint.name
    return (entrypoint.name, cls)


def known_dists():
    """Return a list of all Distributions exporting udata.* entrypoints"""
    return (
        dist
        for dist in pkg_resources.working_set
        if any(k in ENTRYPOINTS for k in dist.get_entry_map().keys())
    )


def get_plugins_dists(app, name=None):
    """Return a list of Distributions with enabled udata plugins"""
    if name:
        plugins = set(e.name for e in iter_all(name) if e.name in app.config["PLUGINS"])
    else:
        plugins = set(app.config["PLUGINS"])
    return [
        d for d in known_dists() if any(set(v.keys()) & plugins for v in d.get_entry_map().values())
    ]


def get_roots(app=None):
    """
    Returns the list of root packages/modules exposing endpoints.

    If app is provided, only returns those of enabled plugins
    """
    roots = set()
    plugins = app.config["PLUGINS"] if app else None
    for name in ENTRYPOINTS.keys():
        for ep in iter_all(name):
            if plugins is None or ep.name in plugins:
                roots.add(ep.module_name.split(".", 1)[0])
    return list(roots)
