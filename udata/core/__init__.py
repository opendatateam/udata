from importlib import import_module

MODULES = (
    'metrics',
    'storages',
    'user',
    'dataset',
    'reuse',
    'organization',
    'activity',
    'followers',
    'topic',
    'post',
)


def init_app(app):
    for module in MODULES:
        module = import_module('udata.core.{0}'.format(module))
        if hasattr(module, 'init_app'):
            module.init_app(app)
