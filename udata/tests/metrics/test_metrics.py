from datetime import datetime, timedelta

import pytest

from udata.core.dataservices.factories import DataserviceFactory
from udata.core.dataservices.models import Dataservice
from udata.core.dataset.factories import DatasetFactory
from udata.core.metrics.helpers import get_metrics_for_model, get_stock_metrics
from udata.core.organization.factories import OrganizationFactory
from udata.core.reuse.factories import ReuseFactory
from udata.core.site.models import Site
from udata.models import Dataset, Organization, Reuse
from udata.tests.api import PytestOnlyDBTestCase

from .helpers import mock_monthly_metrics_payload


@pytest.mark.options(METRICS_API="http://metrics-api.fr/api")
class GetStockMetricsTest(PytestOnlyDBTestCase):
    @pytest.mark.parametrize(
        "target,value_keys",
        [
            ("dataset", ["visit", "download_resource"]),
            ("dataservice", ["visit"]),
            ("reuse", ["visit"]),
            ("organization", ["visit_dataset", "download_resource", "visit_reuse"]),
        ],
    )
    def test_get_metrics_for_model(self, app, rmock, target, value_keys):
        mock_monthly_metrics_payload(
            app, rmock, target, data=[(value_key, 2403) for value_key in value_keys]
        )
        res = get_metrics_for_model(target, "id", value_keys)
        for i, key in enumerate(value_keys):
            assert len(res[i]) == 13  # The current month as well as last year's are included
            assert list(res[i].values())[-1] == len(key) * 2403 + 1
            assert list(res[i].values())[-2] == len(key) * 2403

    def test_get_metrics_for_site(self, app, rmock):
        value_keys = [
            "visit_dataset",
            "download_resource",
        ]
        url = f"{app.config['METRICS_API']}/site/data/?metric_month__sort=desc"
        mock_monthly_metrics_payload(
            app, rmock, "site", data=[(value_key, 2403) for value_key in value_keys], url=url
        )
        res = get_metrics_for_model("site", None, value_keys)
        for i, key in enumerate(value_keys):
            assert len(res[i]) == 13  # The current month as well as last year's are included
            assert list(res[i].values())[-1] == len(key) * 2403 + 1
            assert list(res[i].values())[-2] == len(key) * 2403

    def test_failed_metrics_api_does_not_override_stored_site_metrics(self, app, rmock):
        """A transient metrics API failure must not wipe previously stored metrics."""
        previous_visits = {"2026-05": 42, "2026-06": 51}
        previous_downloads = {"2026-05": 10, "2026-06": 12}
        site = Site(
            id=app.config["SITE_ID"],
            title="Test site",
            metrics={
                "datasets_visits_by_months": previous_visits,
                "resources_downloads_by_months": previous_downloads,
            },
        )
        site.save()

        rmock.get(f"{app.config['METRICS_API']}/site/data/", status_code=500)

        site.count_datasets()
        site.count_resources()

        site.reload()
        assert site.metrics["datasets_visits_by_months"] == previous_visits
        assert site.metrics["resources_downloads_by_months"] == previous_downloads

    @pytest.mark.parametrize(
        "model,factory,date_label",
        [
            (Dataset, DatasetFactory, "created_at_internal"),
            (Dataservice, DataserviceFactory, "created_at"),
            (Reuse, ReuseFactory, "created_at"),
            (Organization, OrganizationFactory, "created_at"),
        ],
    )
    def test_get_stock_metrics(self, model, factory, date_label):
        [factory() for i in range(10)]
        [
            factory(**{date_label: datetime.now().replace(day=1) - timedelta(days=1)})
            for i in range(8)
        ]
        res = get_stock_metrics(model.objects(), date_label)
        assert list(res.values())[-1] == 10
        assert list(res.values())[-2] == 8
        assert list(res.values())[-3] == 0
