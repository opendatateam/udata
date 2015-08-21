# # -*- coding: utf-8 -*-
# from __future__ import unicode_literals

# from udata.models import Dataset, Organization, Reuse
# from udata.tests import TestCase, DBTestMixin, factories

# from .factories import HarvesterFactory

# from ..backends import BaseBackend


# class FakeBackend(BaseBackend):
#     def __init__(self, harvester, orgs=3, datasets=3, reuses=3):
#         self.nb_orgs = orgs
#         self.nb_datasets = datasets
#         self.nb_reuses = reuses
#         super(FakeBackend, self).__init__(harvester)

#     def remote_organizations(self):
#         for i in range(self.nb_orgs):
#             yield factories.OrganizationFactory.build()

#     def remote_datasets(self):
#         for i in range(self.nb_datasets):
#             yield factories.DatasetFactory.build()

#     def remote_reuses(self):
#         for i in range(self.nb_reuses):
#             yield factories.ReuseFactory.build()


# class BaseBackendTest(DBTestMixin, TestCase):
#     def create_app(self):
#         app = super(BaseBackendTest, self).create_app()
#         app.config['PLUGINS'] = ['harvest']
#         return app

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
