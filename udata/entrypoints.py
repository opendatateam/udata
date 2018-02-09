# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import pkg_resources

# Here for documention purpose
ENTRYPOINTS = {
    'udata.avatars': 'Avatar rendering backends',
    'udata.harvesters': 'Harvest backends',
    'udata.i18n': 'Extra translations',
    'udata.linkcheckers': 'Link checker backends',
    'udata.themes': 'Themes',
    'udata.views': 'Extra views',
}


class EntrypointError(Exception):
    pass


def iter(name):
    '''Iter all entrypoints registered on a given key'''
    return pkg_resources.iter_entry_points(name)


def get_all(entrypoint_key):
    '''Load all entrypoints registered on a given key'''
    return dict(_ep_to_kv(e) for e in iter(entrypoint_key))


def get_enabled(name, app):
    '''
    Get (and load) entrypoints registered on name
    and enabled for the given app.
    '''
    plugins = app.config['PLUGINS']
    return dict(_ep_to_kv(e) for e in iter(name) if e.name in plugins)


def _ep_to_kv(entrypoint):
    '''
    Transform an entrypoint into a key-value tuple where:
    - key is the entrypoint name
    - value is the entrypoint class with the name attribute
      matching from entrypoint name
    '''
    cls = entrypoint.load()
    cls.name = entrypoint.name
    return (entrypoint.name, cls)


def known_dists():
    '''Return a list of all Distributions exporting udata.* entrypoints'''
    return (
        dist for dist in pkg_resources.working_set
        if any(k in ENTRYPOINTS for k in dist.get_entry_map().keys())
    )


def get_plugins_dists(app):
    '''Return a list of Distributions with enabled udata plugins'''
    plugins = set(app.config['PLUGINS'])
    return [
        d for d in known_dists()
        if any(set(v.keys()) & plugins for v in d.get_entry_map().values())
    ]


def get_roots():
    '''
    Returns the list of root packages/modules exposing endpoints.
    '''
    roots = set()
    for name in ENTRYPOINTS.keys():
        for ep in iter(name):
            roots.add(ep.module_name.split('.', 1)[0])
    return list(roots)
