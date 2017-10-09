# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import pkg_resources


def get_all(entrypoint_key):
    return dict(
        _ep_to_kv(e) for e in pkg_resources.iter_entry_points(entrypoint_key)
    )


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
