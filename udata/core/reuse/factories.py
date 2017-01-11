# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import factory
from factory.mongoengine import MongoEngineFactory
from factory.fuzzy import FuzzyChoice

from udata import models, utils
from udata.core.dataset.factories import DatasetFactory
from udata.utils import faker


class ReuseFactory(MongoEngineFactory):
    class Meta:
        model = models.Reuse

    title = factory.LazyAttribute(lambda o: faker.sentence())
    description = factory.LazyAttribute(lambda o: faker.text())
    url = factory.LazyAttribute(
        lambda o: '/'.join([faker.url(), utils.unique_string()]))
    type = FuzzyChoice(models.REUSE_TYPES.keys())


class VisibleReuseFactory(ReuseFactory):
    @factory.lazy_attribute
    def datasets(self):
        return [DatasetFactory()]
