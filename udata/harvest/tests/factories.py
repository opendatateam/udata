from typing import Never

import factory
import pytest
from factory.fuzzy import FuzzyChoice
from flask.signals import Namespace
from typing_extensions import override

from udata.core.dataset.models import Dataset
from udata.factories import ModelFactory

from ..backends import BaseBackend, Harvestable, HarvestExtraConfig, HarvestFeature, HarvestFilter
from ..models import HarvestItem, HarvestJob, HarvestSource


def dtfactory(start, end):
    return factory.Faker("date_time_between", start_date=start, end_date=end)


class HarvestSourceFactory(ModelFactory):
    class Meta:
        model = HarvestSource

    name = factory.Faker("name")
    url = factory.Faker("url")
    description = factory.Faker("text")
    backend = "factory"


class HarvestJobFactory(ModelFactory):
    class Meta:
        model = HarvestJob

    created = dtfactory("-3h", "-2h")
    started = dtfactory("-2h", "-1h")
    ended = dtfactory("-1h", "now")
    status = FuzzyChoice(HarvestJob.status.choices)
    source = factory.SubFactory(HarvestSourceFactory)


ns = Namespace()

mock_initialize = ns.signal("backend:initialize")
mock_process = ns.signal("backend:process")

DEFAULT_COUNT = 3


class FactoryBackend(BaseBackend):
    name = "factory"
    filters = (
        HarvestFilter("Test", "test", int, "An integer"),
        HarvestFilter("Tag", "tag", str),
    )
    features = (
        HarvestFeature("test", "Test"),
        HarvestFeature("toggled", "Toggled", "A togglable", True),
    )
    extra_configs = (
        HarvestExtraConfig("Test Int", "test_int", int, "An integer"),
        HarvestExtraConfig("Test Str", "test_str", str),
    )

    @override
    def inner_harvest(self) -> Never:
        mock_initialize.send(self)
        for i in range(self.config.get("count", DEFAULT_COUNT)):
            self.process_item(Dataset, str(i))
            if self.has_reached_max_items():
                return

    @override
    def inner_process(
        self, item_class: type[Harvestable], harvest_item: HarvestItem, **kwargs
    ) -> Harvestable | None:
        mock_process.send(self, item=harvest_item.remote_id)

        item = self.get_item(item_class, harvest_item.remote_id)
        item.title = f"{item_class.__name__.lower()}-{harvest_item.remote_id}"

        return item


class MockBackendsMixin(object):
    """A mixin mocking the harvest backend"""

    @pytest.fixture(autouse=True)
    def mock_backend(self, mocker):
        return_value = {"factory": FactoryBackend}
        mocker.patch("udata.harvest.backends.get_all_backends", return_value=return_value)
