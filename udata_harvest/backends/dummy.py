# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

import logging

from . import register
from .base import BaseBackend

log = logging.getLogger(__name__)


@register
class DummyBackend(BaseBackend):
    name = 'dummy'

    '''A backend doing nothing, mai,ly for testing purpose'''
    def initialize(self, job):
        pass

    def process_item(self, item):
        pass
