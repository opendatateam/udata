from typing import Never

import factory
import pytest
from factory.fuzzy import FuzzyChoice
from flask.signals import Namespace
from typing_extensions import override

from udata.core.dataservices.models import Dataservice
from udata.core.dataset.models import Dataset
from udata.factories import ModelFactory

from .. import backends
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


class FactoryBackend(backends.BaseBackend):
    name = "factory"
    filters = (
        backends.HarvestFilter("Test", "test", int, "An integer"),
        backends.HarvestFilter("Tag", "tag", str),
    )
    features = (
        backends.HarvestFeature("test", "Test"),
        backends.HarvestFeature("toggled", "Toggled", "A togglable", True),
    )
    extra_configs = (
        backends.HarvestExtraConfig("Test Int", "test_int", int, "An integer"),
        backends.HarvestExtraConfig("Test Str", "test_str", str),
    )

    @override
    def inner_harvest(self) -> Never:
        mock_initialize.send(self)
        for i in range(self.config.get("count", DEFAULT_COUNT)):
            self.process_dataset(str(i))
            if self.has_reached_max_items():
                return

    @override
    def inner_process_dataset(self, item: HarvestItem, **kwargs) -> Dataset:
        mock_process.send(self, item=item.remote_id)

        dataset = self.get_dataset(item.remote_id)
        dataset.title = f"dataset-{item.remote_id}"

        return dataset

    @override
    def inner_process_dataservice(self, item: HarvestItem, **kwargs) -> Dataservice:
        # FIXME: doesn't return Dataservice...
        pass


class MockBackendsMixin(object):
    """A mixin mocking the harvest backend"""

    @pytest.fixture(autouse=True)
    def mock_backend(self, mocker):
        return_value = {"factory": FactoryBackend}
        mocker.patch("udata.harvest.backends.get_all_backends", return_value=return_value)
