import io
import json
import os
import pkg_resources

from flask import current_app, request, url_for
from flask_cdn import url_for as cdn_url_for

# Store manifests URLs with the following hierarchy
# app > filename (without hash) > URL
_manifests = {}

_registered_manifests = {}  # Here for debug without cache


def has_manifest(app, filename='manifest.json'):
    '''Verify the existance of a JSON assets manifest'''
    try:
        return pkg_resources.resource_exists(app, filename)
    except (ImportError, NotImplementedError):
        return os.path.isabs(filename) and os.path.exists(filename)


def register_manifest(app, filename='manifest.json'):
    '''Register an assets json manifest'''
    if current_app.config.get('TESTING'):
        return  # Do not spend time here when testing
    # only try to use the package parsing method if it's not a full path
    if not os.path.isabs(filename) and not has_manifest(app, filename):
        msg = '{filename} not found for {app}'.format(**locals())
        raise ValueError(msg)
    manifest = _manifests.get(app, {})
    manifest.update(load_manifest(app, filename))
    _manifests[app] = manifest


def load_manifest(app, filename='manifest.json'):
    '''Load an assets json manifest'''
    if os.path.isabs(filename):
        path = filename
    else:
        path = pkg_resources.resource_filename(app, filename)
    with io.open(path, mode='r', encoding='utf8') as stream:
        data = json.load(stream)
    _registered_manifests[app] = path
    return data


def exists_in_manifest(app, filename):
    '''
    Test wether a static file exists in registered manifests or not
    '''
    return app in _manifests and filename in _manifests[app]


def from_manifest(app, filename, raw=False, **kwargs):
    '''
    Get the path to a static file for a given app entry of a given type.

    :param str app: The application key to which is tied this manifest
    :param str filename: the original filename (without hash)
    :param bool raw: if True, doesn't add prefix to the manifest
    :return: the resolved file path from manifest
    :rtype: str
    '''
    cfg = current_app.config

    if current_app.config.get('TESTING'):
        return  # Do not spend time here when testing

    path = _manifests[app][filename]

    if not raw and cfg.get('CDN_DOMAIN') and not cfg.get('CDN_DEBUG'):
        scheme = 'https' if cfg.get('CDN_HTTPS') else request.scheme
        prefix = '{}://'.format(scheme)
        if not path.startswith('/'):  # CDN_DOMAIN has no trailing slash
            path = '/' + path
        return ''.join((prefix, cfg['CDN_DOMAIN'], path))
    elif not raw and kwargs.get('external', False):
        if path.startswith('/'):  # request.host_url has a trailing slash
            path = path[1:]
        return ''.join((request.host_url, path))
    return path


def manifests_paths():
    return _registered_manifests.values()


def cdn_for(endpoint, **kwargs):
    '''
    Get a CDN URL for a static assets.

    Do not use a replacement for all flask.url_for calls
    as it is only meant for CDN assets URLS.
    (There is some extra round trip which cost is justified
    by the CDN assets prformance improvements)
    '''
    if current_app.config['CDN_DOMAIN']:
        if not current_app.config.get('CDN_DEBUG'):
            kwargs.pop('_external', None)  # Avoid the _external parameter in URL
        return cdn_url_for(endpoint, **kwargs)
    return url_for(endpoint, **kwargs)
