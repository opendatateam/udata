# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import factory

from factory.mongoengine import MongoEngineFactory
from faker import Faker

from udata.tests.factories import UserFactory

from ..models import Harvester

fake = Faker()


class HarvesterFactory(MongoEngineFactory):
    FACTORY_FOR = Harvester

    name = factory.LazyAttribute(lambda o: fake.first_name())
    description = factory.LazyAttribute(lambda o: fake.text())
    config = factory.LazyAttribute(lambda o: {'user': str(UserFactory().id)})
