# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import factory

from factory.mongoengine import MongoEngineFactory
from faker import Faker

from ..models import HarvestSource, HarvestJob

fake = Faker()


def dtfactory(start, end):
    return factory.LazyAttribute(
        lambda o: fake.date_time_between(start_date=start, end_date=end))


class HarvestSourceFactory(MongoEngineFactory):
    class Meta:
        model = HarvestSource

    name = factory.LazyAttribute(lambda o: fake.name())
    description = factory.LazyAttribute(lambda o: fake.text())


class HarvestJobFactory(MongoEngineFactory):
    class Meta:
        model = HarvestJob

    created = dtfactory('-3h', '-2h')
    started = dtfactory('-2h', '-1h')
    ended = dtfactory('-1h', 'new')
    status = factory.fuzzy.FuzzyChoice(HarvestJob.status.choices)
    source = factory.SubFactory(HarvestSourceFactory)
