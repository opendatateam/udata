import pytest

from udata.core.dataset.factories import DatasetFactory, VisibleDatasetFactory
from udata.core.site.factories import SiteFactory
from udata.models import Site
from udata.core.site.models import current_site
from udata.tests.helpers import assert_emit


@pytest.mark.usefixtures('clean_db')
class SiteMetricTest:
    def test_dataset_metric(self, app):
        site = SiteFactory.create(
            id=app.config['SITE_ID']
        )
        DatasetFactory.create_batch(2)
        VisibleDatasetFactory.create_batch(3)

        site.count_datasets()

        assert site.get_metrics()['datasets'] == 3

    def test_resources_metric(self, app):
        site = SiteFactory.create(
            id=app.config['SITE_ID']
        )

        DatasetFactory.create_batch(3, nb_resources=3)

        site.count_datasets()
        site.count_resources()

        assert site.get_metrics()['resources'] == 9
