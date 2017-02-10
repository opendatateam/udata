# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime

from udata.core.dataset.factories import DatasetFactory
from udata.core.site.models import current_site
from udata.core.reuse.factories import ReuseFactory

from udata.tests import TestCase, DBTestMixin


class SiteModelTest(DBTestMixin, TestCase):
    def test_delete_home_dataset(self):
        '''Should pull home datasets on deletion'''
        current_site.settings.home_datasets = DatasetFactory.create_batch(3)
        current_site.save()

        dataset = current_site.settings.home_datasets[1]
        dataset.deleted = datetime.now()
        dataset.save()

        current_site.reload()
        home_datasets = [d.id for d in current_site.settings.home_datasets]
        self.assertEqual(len(home_datasets), 2)
        self.assertNotIn(dataset.id, home_datasets)

    def test_delete_home_reuse(self):
        '''Should pull home reuses on deletion'''
        current_site.settings.home_reuses = ReuseFactory.create_batch(3)
        current_site.save()

        reuse = current_site.settings.home_reuses[1]
        reuse.deleted = datetime.now()
        reuse.save()

        current_site.reload()
        home_reuses = [r.id for r in current_site.settings.home_reuses]
        self.assertEqual(len(home_reuses), 2)
        self.assertNotIn(reuse.id, home_reuses)
