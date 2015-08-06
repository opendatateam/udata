# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

import logging

from . import register
from .base import BaseBackend

log = logging.getLogger(__name__)


@register
class DummyBackend(BaseBackend):
    '''A backend doing nothing, mainly for testing purpose'''
    name = 'dummy'

    def initialize(self, job):
        pass

    def process_item(self, item):
        pass
