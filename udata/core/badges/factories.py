# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from factory.mongoengine import MongoEngineFactory
from factory.fuzzy import FuzzyChoice

from udata import models
from udata.utils import faker


def badge_factory(model):
    class BadgeFactory(MongoEngineFactory):
        class Meta:
            model = models.Badge

        kind = FuzzyChoice(model.__badges__.keys())

    return BadgeFactory
