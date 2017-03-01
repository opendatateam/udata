# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import factory

from factory.fuzzy import FuzzyChoice

from .models import Badge


def badge_factory(model):
    class BadgeFactory(factory.mongoengine.MongoEngineFactory):
        class Meta:
            model = Badge

        kind = FuzzyChoice(model.__badges__.keys())

    return BadgeFactory
