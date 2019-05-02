'''
A registry module for metrics
'''

_catalog = {}


def register(metric):
    '''Register a metric class'''
    if metric.model not in _catalog:
        _catalog[metric.model] = {}
    _catalog[metric.model][metric.name] = metric


def get_for(cls):
    '''
    Get metrics registered for a given class.

    :returns: A dict(name)->spec
    '''
    return _catalog.get(cls, {})


def items():
    '''Iterate over models and their metrics'''
    for cls, metrics in _catalog.items():
        yield cls, metrics
