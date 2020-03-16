import pytest

import udata.core.site.metrics
from udata.core.dataset.factories import DatasetFactory, VisibleDatasetFactory
from udata.core.site.factories import SiteFactory
from udata.models import Site
from udata.core.site.models import current_site
from udata.tests.helpers import assert_emit


@pytest.mark.usefixtures('clean_db')
class SiteMetricTest:
    def test_dataset_metric(self, app):
        DatasetFactory.create_batch(2)
        VisibleDatasetFactory.create_batch(3)

        site = Site.objects.get(id=app.config['SITE_ID'])

        assert site.get_metrics['datasets'] == 3

    def test_resources_metric(self, app):
        DatasetFactory.create_batch(3, nb_resources=3)

        site = Site.objects.get(id=app.config['SITE_ID'])

        assert site.get_metrics['resources'] == 9