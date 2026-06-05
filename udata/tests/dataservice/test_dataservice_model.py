from datetime import UTC, datetime

from flask import current_app

from udata.core import metrics
from udata.core.dataservices.factories import DataserviceFactory
from udata.core.reuse.factories import ReuseFactory
from udata.models import Reuse
from udata.tests.api import PytestOnlyDBTestCase
from udata.tests.helpers import assert_emit


class DataserviceModelTest(PytestOnlyDBTestCase):
    def test_dataservice_reuses_metric(self):
        # We need to init metrics module
        metrics.init_app(current_app)

        dataservice = DataserviceFactory()

        # Attach a reuse to the dataservice
        with assert_emit(Reuse.on_create):
            reuse = ReuseFactory(dataservices=[dataservice])
            # An unrelated reuse should not be counted
            ReuseFactory()

        dataservice.reload()
        assert dataservice.get_metrics()["reuses"] == 1

        # Delete the reuse
        with assert_emit(Reuse.on_delete):
            reuse.deleted = datetime.now(UTC)
            reuse.save()

        dataservice.reload()
        assert dataservice.get_metrics()["reuses"] == 0

        # Attach and then detach the reuse
        reuse = ReuseFactory(dataservices=[dataservice])

        dataservice.reload()
        assert dataservice.get_metrics()["reuses"] == 1

        with assert_emit(Reuse.on_update):
            reuse.dataservices = []
            reuse.save()

        dataservice.reload()
        assert dataservice.get_metrics()["reuses"] == 0
