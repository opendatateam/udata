# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import factory

from faker.providers.date_time import Provider as DTProvider

from .models import DateRange
from .utils import faker_provider


# Until https://github.com/joke2k/faker/pull/596 is merged

@faker_provider
class DateTimeProvider(DTProvider):
    def date_between(self, start_date='-30y', end_date='now'):
        return self.date_time_between(start_date=start_date,
                                      end_date=end_date).date()


class ModelFactory(factory.mongoengine.MongoEngineFactory):
    class Meta:
        abstract = True

    @classmethod
    def as_dict(cls, **kwargs):
        return factory.build(dict, FACTORY_CLASS=cls, **kwargs)


class DateRangeFactory(ModelFactory):
    class Meta:
        model = DateRange

    start = factory.Faker('date_between', start_date='-10y', end_date='-5y')
    end = factory.Faker('date_between', start_date='-5y', end_date='-2y')
