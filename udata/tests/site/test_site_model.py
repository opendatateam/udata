from datetime import datetime

from flask import current_app, g

from udata.core.dataset.factories import DatasetFactory
from udata.core.reuse.factories import ReuseFactory
from udata.core.site.models import Site, current_site, get_current_site
from udata.tests import DBTestMixin, TestCase


class SiteModelTest(DBTestMixin, TestCase):
    def test_current_site(self):
        current_app.config["SITE_ID"] = "old-id"
        current_app.config["SITE_TITLE"] = "Test"

        assert Site.objects.count() == 0

        g.site = None
        site_1 = get_current_site()
        assert Site.objects.count() == 1
        assert site_1.id == "old-id"
        assert site_1.title == "Test"

        g.site = None
        current_app.config["SITE_TITLE"] = "New name"
        site_2 = get_current_site()
        assert Site.objects.count() == 1
        assert site_2.id == "old-id"
        assert site_2.title == "New name"

        g.site = None
        current_app.config["SITE_ID"] = "new-id"
        site_3 = get_current_site()
        assert Site.objects.count() == 2
        assert site_3.id == "new-id"
        assert site_3.title == "New name"

    def test_delete_home_dataset(self):
        """Should pull home datasets on deletion"""
        current_site.settings.home_datasets = DatasetFactory.create_batch(3)
        current_site.save()

        dataset = current_site.settings.home_datasets[1]
        dataset.deleted = datetime.utcnow()
        dataset.save()

        current_site.reload()
        home_datasets = [d.id for d in current_site.settings.home_datasets]
        self.assertEqual(len(home_datasets), 2)
        self.assertNotIn(dataset.id, home_datasets)

    def test_delete_home_reuse(self):
        """Should pull home reuses on deletion"""
        current_site.settings.home_reuses = ReuseFactory.create_batch(3)
        current_site.save()

        reuse = current_site.settings.home_reuses[1]
        reuse.deleted = datetime.utcnow()
        reuse.save()

        current_site.reload()
        home_reuses = [r.id for r in current_site.settings.home_reuses]
        self.assertEqual(len(home_reuses), 2)
        self.assertNotIn(reuse.id, home_reuses)
