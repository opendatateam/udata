# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import


class HarvestException(Exception):
    '''Base class for all harvest exception'''
    pass


class HarvestSkipException(HarvestException):
    '''Raised when an item is skipped'''
    pass
