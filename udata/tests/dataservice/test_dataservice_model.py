import pytest

from udata.core.dataservices.factories import DataserviceFactory
from udata.core.dataservices.models import Dataservice
from udata.core.dataset.factories import DatasetFactory

pytestmark = pytest.mark.usefixtures("clean_db")


class DataserviceModelTest:
    def test_empty_datasets(self):
        dataservice = DataserviceFactory()
        dataset = DatasetFactory()
        # If we're not setting the datasets ListField, it's set to the empty list.
        assert "datasets" in Dataservice._get_collection().find_one({"_id": dataservice.pk})
        assert dataservice.datasets == []

        # Setting it explicitely to a non-empty list should work as expected
        dataservice.datasets = [dataset]
        dataservice.save()
        assert "datasets" in Dataservice._get_collection().find_one({"_id": dataservice.pk})
        assert dataservice.datasets == [dataset]

        # See https://github.com/MongoEngine/mongoengine/issues/267#issuecomment-283065318
        # Setting it explicitely to an empty list should NOT remove the field.
        dataservice.datasets = []
        dataservice.save()
        # dataservice.update(add_to_set__datasets=[])
        assert dataservice.datasets == []
        assert "datasets" in Dataservice._get_collection().find_one({"_id": dataservice.pk})
