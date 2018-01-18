# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from factory.fuzzy import FuzzyChoice

from udata.factories import ModelFactory

from .models import Badge


def badge_factory(model):
    class BadgeFactory(ModelFactory):
        class Meta:
            model = Badge

        kind = FuzzyChoice(model.__badges__.keys())

    return BadgeFactory
