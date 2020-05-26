from datetime import date

from flask import url_for

from udata.core.site.models import Site
from udata.core.site.models import current_site
from udata.core.site.factories import SiteFactory
from udata.core.dataset.factories import VisibleDatasetFactory
from udata.core.reuse.factories import VisibleReuseFactory
from udata.core.user.factories import AdminFactory

from udata.tests.api import APITestCase


class SiteAPITest(APITestCase):
    modules = ['core.site', 'core.dataset', 'core.reuse', 'core.organization']

    def test_get_site(self):
        response = self.get(url_for('api.site'))
        self.assert200(response)

    def test_get_home_datasets(self):
        site = SiteFactory.create(
            id=self.app.config['SITE_ID'],
            settings__home_datasets=VisibleDatasetFactory.create_batch(3)
        )
        current_site.reload()

        self.login(AdminFactory())
        response = self.get(url_for('api.home_datasets'))
        self.assert200(response)

        self.assertEqual(len(response.json), len(site.settings.home_datasets))

    def test_get_home_reuses(self):
        site = SiteFactory.create(
            id=self.app.config['SITE_ID'],
            settings__home_reuses=VisibleReuseFactory.create_batch(3)
        )
        current_site.reload()

        self.login(AdminFactory())
        response = self.get(url_for('api.home_reuses'))
        self.assert200(response)

        self.assertEqual(len(response.json), len(site.settings.home_reuses))

    def test_set_home_datasets(self):
        ids = [d.id for d in VisibleDatasetFactory.create_batch(3)]

        self.login(AdminFactory())
        response = self.put(url_for('api.home_datasets'), ids)

        self.assert200(response)
        self.assertEqual(len(response.json), len(ids))

        site = Site.objects.get(id=self.app.config['SITE_ID'])

        self.assertEqual([d.id for d in site.settings.home_datasets], ids)

    def test_set_home_reuses(self):
        ids = [r.id for r in VisibleReuseFactory.create_batch(3)]

        self.login(AdminFactory())
        response = self.put(url_for('api.home_reuses'), ids)

        self.assert200(response)
        self.assertEqual(len(response.json), len(ids))

        site = Site.objects.get(id=self.app.config['SITE_ID'])

        self.assertEqual([r.id for r in site.settings.home_reuses], ids)
