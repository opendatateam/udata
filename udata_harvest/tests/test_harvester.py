# # -*- coding: utf-8 -*-
# from __future__ import unicode_literals

# from udata.models import Dataset, Organization, Reuse
# from udata.tests import TestCase, DBTestMixin, factories

# from .factories import HarvestSourceFactory

# from ..harvester import Harvester


# class TestHarvester(Harvester):
#     name = 'test'

#     def initialize(self):
#         pass

#     def process(self, data, *args, **kwargs):
#         pass


# class HarvesterTest(DBTestMixin, TestCase):
#     def create_app(self):
#         app = super(HarvesterTest, self).create_app()
#         app.config['PLUGINS'] = ['harvest']
#         return app

#     def test

#     def test_harvest_all(self):
#         backend = FakeBackend(HarvesterFactory())

#         backend.harvest()

#         self.assertEqual(Organization.objects.count(), backend.nb_orgs)
#         self.assertEqual(Dataset.objects.count(), backend.nb_datasets)
#         self.assertEqual(Reuse.objects.count(), backend.nb_reuses)

#     def test_harvest_one(self):
#         backend = FakeBackend(HarvesterFactory())

#         backend.harvest(reuses=True)

#         self.assertEqual(Organization.objects.count(), 0)
#         self.assertEqual(Dataset.objects.count(), 0)
#         self.assertEqual(Reuse.objects.count(), backend.nb_reuses)

#     def test_harvest_two(self):
#         backend = FakeBackend(HarvesterFactory())

#         backend.harvest(datasets=True, reuses=True)

#         self.assertEqual(Organization.objects.count(), 0)
#         self.assertEqual(Dataset.objects.count(), backend.nb_datasets)
#         self.assertEqual(Reuse.objects.count(), backend.nb_reuses)
