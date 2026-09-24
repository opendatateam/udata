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
        metrics.init_app(current_app)

        dataservice = DataserviceFactory()

        with assert_emit(Reuse.on_create):
            reuse = ReuseFactory(dataservices=[dataservice])
            ReuseFactory()

        dataservice.reload()
        assert dataservice.get_metrics()["reuses"] == 1

        with assert_emit(Reuse.on_delete):
            reuse.deleted = datetime.now(UTC)
            reuse.save()

        dataservice.reload()
        assert dataservice.get_metrics()["reuses"] == 0

        reuse = ReuseFactory(dataservices=[dataservice])

        dataservice.reload()
        assert dataservice.get_metrics()["reuses"] == 1

        with assert_emit(Reuse.on_update):
            reuse.dataservices = []
            reuse.save()

        dataservice.reload()
        assert dataservice.get_metrics()["reuses"] == 0
