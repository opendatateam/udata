# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import factory

from factory.fuzzy import FuzzyChoice
from factory.mongoengine import MongoEngineFactory
from faker import Faker

from udata.tests.factories import UserFactory

from ..models import HarvestSource, HARVEST_FREQUENCIES

fake = Faker()


# class HarvesterFactory(MongoEngineFactory):
#     FACTORY_FOR = Harvester

#     name = factory.LazyAttribute(lambda o: fake.first_name())
#     description = factory.LazyAttribute(lambda o: fake.text())
#     config = factory.LazyAttribute(lambda o: {'user': str(UserFactory().id)})


class HarvestSourceFactory(MongoEngineFactory):
    class Meta:
        model = HarvestSource

    name = factory.LazyAttribute(lambda o: fake.name())
    description = factory.LazyAttribute(lambda o: fake.text())
    frequency = FuzzyChoice([k for k, v in HARVEST_FREQUENCIES])
