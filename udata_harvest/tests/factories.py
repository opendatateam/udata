# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import factory

from factory.mongoengine import MongoEngineFactory
from faker import Faker

from ..models import HarvestSource

fake = Faker()


class HarvestSourceFactory(MongoEngineFactory):
    class Meta:
        model = HarvestSource

    name = factory.LazyAttribute(lambda o: fake.name())
    description = factory.LazyAttribute(lambda o: fake.text())
