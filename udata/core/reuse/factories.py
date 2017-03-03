# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import factory

from factory.fuzzy import FuzzyChoice

from udata.core.dataset.factories import DatasetFactory
from udata.utils import faker

from .models import Reuse, REUSE_TYPES


class ReuseFactory(factory.mongoengine.MongoEngineFactory):
    class Meta:
        model = Reuse

    title = factory.Faker('sentence')
    description = factory.Faker('text')
    url = factory.LazyAttribute(
        lambda o: '/'.join([faker.url(), faker.unique_string()]))
    type = FuzzyChoice(REUSE_TYPES.keys())


class VisibleReuseFactory(ReuseFactory):
    @factory.lazy_attribute
    def datasets(self):
        return [DatasetFactory()]
