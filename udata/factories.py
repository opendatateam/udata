import factory

from .models import DateRange


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
