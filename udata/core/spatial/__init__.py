# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.i18n import lazy_gettext as _


LEVELS = {
    'country-group': {'label': _('Country group'),  'children': ['country'], 'position': 0},
    'country': {'label': _('Country'), 'parent': 'country-group', 'children': ['country-subset'], 'position': 1},
    'country-subset': {'label': _('Country subset'), 'parent': 'country', 'children': [], 'position': 2},
}


def register_level(parent, key, label):
    '''Attach an administrative level to its parent'''
    if parent not in LEVELS:
        raise ValueError('Parent level "{0}" does not exists'.format(parent))
    parent_level = LEVELS[parent]
    position = parent_level['position'] + 1
    level = {'label': label, 'parent': parent, 'children': [], 'position': position}
    LEVELS[key] = level
    parent_level['children'].append(key)
    return level


def register_level_tree(parent, levels):
    '''Register a complete territory level tree'''
    for key, label in levels:
        register_level(parent, key, label)
        parent = key
