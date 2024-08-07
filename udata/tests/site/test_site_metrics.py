import pytest

from udata.core.dataset.factories import (
    DatasetFactory,
    HiddenDatasetFactory,
    OrganizationFactory,
)
from udata.core.organization.constants import PUBLIC_SERVICE
from udata.core.reuse.factories import VisibleReuseFactory
from udata.core.site.factories import SiteFactory
from udata.harvest.tests.factories import HarvestSourceFactory
from udata.models import Badge


@pytest.mark.usefixtures("clean_db")
class SiteMetricTest:
    def test_orga_metric(self, app):
        site = SiteFactory.create(id=app.config["SITE_ID"])
        OrganizationFactory.create_batch(3)

        site.count_org()

        assert site.get_metrics()["organizations"] == 3

    def test_reuse_metric(self, app):
        site = SiteFactory.create(id=app.config["SITE_ID"])
        VisibleReuseFactory.create_batch(4)

        site.count_reuses()

        assert site.get_metrics()["reuses"] == 4

    def test_dataset_metric(self, app):
        site = SiteFactory.create(id=app.config["SITE_ID"])
        DatasetFactory.create_batch(2)
        HiddenDatasetFactory.create_batch(3)

        site.count_datasets()

        assert site.get_metrics()["datasets"] == 2

    def test_resources_metric(self, app):
        site = SiteFactory.create(id=app.config["SITE_ID"])

        DatasetFactory.create_batch(3, nb_resources=3)

        site.count_datasets()
        site.count_resources()

        assert site.get_metrics()["resources"] == 9

    def test_badges_metric(self, app):
        site = SiteFactory.create(id=app.config["SITE_ID"])

        ps_badge = Badge(kind=PUBLIC_SERVICE)
        public_services = [OrganizationFactory(badges=[ps_badge]) for _ in range(2)]
        for _ in range(3):
            OrganizationFactory()

        site.count_org_for_badge(PUBLIC_SERVICE)

        assert site.get_metrics()[PUBLIC_SERVICE] == len(public_services)

    def test_harvesters_metric(self, app):
        site = SiteFactory.create(id=app.config["SITE_ID"])
        sources = [HarvestSourceFactory() for i in range(10)]

        site.count_harvesters()

        assert site.get_metrics()["harvesters"] == len(sources)
