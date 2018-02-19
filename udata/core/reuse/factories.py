# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import factory

from factory.fuzzy import FuzzyChoice

from udata.core.dataset.factories import DatasetFactory
from udata.factories import ModelFactory
from udata.utils import faker

from .models import Reuse, REUSE_TYPES


class ReuseFactory(ModelFactory):
    class Meta:
        model = Reuse

    title = factory.Faker('sentence')
    description = factory.Faker('text')
    url = factory.LazyAttribute(
        lambda o: '/'.join([faker.url(), faker.unique_string()]))
    type = FuzzyChoice(REUSE_TYPES.keys())

    class Params:
        visible = factory.Trait(
            datasets=factory.LazyAttribute(lambda o: [DatasetFactory()])
        )


class VisibleReuseFactory(ReuseFactory):
    @factory.lazy_attribute
    def datasets(self):
        return [DatasetFactory()]
