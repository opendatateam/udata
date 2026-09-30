import itertools
from typing import TYPE_CHECKING, TypeVar

import factory

from udata.mongo.datetime_fields import DateRange

T = TypeVar("T")

if TYPE_CHECKING:
    _ModelFactoryBase = factory.mongoengine.MongoEngineFactory[T]
else:
    _ModelFactoryBase = factory.mongoengine.MongoEngineFactory


class ModelFactory(_ModelFactoryBase):
    class Meta:
        abstract = True

    @classmethod
    def as_dict(cls, **kwargs):
        return factory.build(dict, FACTORY_CLASS=cls, **kwargs)


class DateRangeFactory(ModelFactory):
    class Meta:
        model = DateRange

    start = factory.Faker("date_between", start_date="-10y", end_date="-5y")
    end = factory.Faker("date_between", start_date="-5y", end_date="-2y")


class HarvestableFactoryMixin(_ModelFactoryBase):
    class Meta:
        abstract = True

    # FIXME: reset like factory does
    _ids = itertools.count()

    @factory.post_generation
    def remote_id(obj, create, extracted, **kwargs):
        """Sets the obj.remote_id attribute. In-memory only, not saved in the mongo document.

        If remote_id parameter passed to the factory is:
        - falsy => attribute not set
        - True => attribute set to "dataset-0", "dataset-1", ...
        - string => attribute set to string value (will collide if more than one instance share the same id)
        - callable(i) => attribute set to returned value (with i a sequence number)
        """
        if extracted is True:
            extracted = lambda i: f"{type(obj).__name__.lower()}-{i}"  # noqa: E731
        if callable(extracted):
            extracted = extracted(next(HarvestableFactoryMixin._ids))
        if extracted:
            obj.remote_id = extracted
