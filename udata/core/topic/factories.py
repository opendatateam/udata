import factory

from udata import utils
from udata.core.dataset.factories import DatasetFactory
from udata.core.reuse.factories import ReuseFactory
from udata.factories import ModelFactory

from .models import Topic, TopicElement


class TopicElementFactory(ModelFactory):
    class Meta:
        model = TopicElement

    title = factory.Faker("sentence")
    description = factory.Faker("text")

    @classmethod
    def element_as_payload(cls, elt) -> dict:
        return {
            "element": {"id": str(elt["element"].id), "class": elt["element"].__class__.__name__},
            "title": elt["title"],
            "description": elt["description"],
        }

    @classmethod
    def as_payload(cls) -> dict:
        elt = cls.as_dict()
        return cls.element_as_payload(elt)


class TopicElementDatasetFactory(TopicElementFactory):
    element = factory.SubFactory(DatasetFactory)


class TopicElementReuseFactory(TopicElementFactory):
    element = factory.SubFactory(ReuseFactory)


class TopicFactory(ModelFactory):
    class Meta:
        model = Topic

    name = factory.Faker("sentence")
    description = factory.Faker("text")
    tags = factory.LazyAttribute(lambda o: [utils.unique_string(16) for _ in range(3)])
    private = False

    @factory.lazy_attribute
    def elements(self):
        return [*TopicElementDatasetFactory.create_batch(2), TopicElementReuseFactory()]

    @classmethod
    def elements_as_payload(cls, elements: list) -> dict:
        return [
            {
                "element": {"id": str(elt.element.id), "class": elt.element.__class__.__name__},
                "title": elt.title,
                "description": elt.description,
                "tags": elt.tags,
                "extras": elt.extras,
            }
            for elt in elements
        ]

    @classmethod
    def as_payload(cls) -> dict:
        payload = cls.as_dict()
        payload["elements"] = cls.elements_as_payload(payload["elements"])
        return payload
