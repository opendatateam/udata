# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from udata import models
from udata.commands.fixtures import (
    generate_fixtures, generate_reuses, generate_datasets, generate_licenses
)
from udata.core.user.factories import UserFactory
from udata.tests import TestCase, DBTestMixin


class FixturesTest(DBTestMixin, TestCase):

    def test_generate_datasets(self):
        generate_datasets(count=2)
        self.assertEqual(models.Dataset.objects.count(), 2)
        self.assertEqual(models.DatasetDiscussion.objects.count(), 2)

    def test_generate_reuses(self):
        generate_reuses(count=2)
        self.assertEqual(models.Reuse.objects.count(), 2)
        user = UserFactory()
        generate_reuses(count=1, user=user)
        self.assertEqual(models.Reuse.objects(owner=user).count(), 1)

    def test_generate_licenses(self):
        generate_licenses(count=2)
        self.assertEqual(models.License.objects.count(), 2)

    def test_generate_fixtures(self):
        generate_fixtures()
        self.assertEqual(models.Dataset.objects.count(), 10)
        self.assertEqual(models.DatasetDiscussion.objects.count(), 5)
        self.assertEqual(models.Reuse.objects.count(), 5)
        self.assertEqual(models.License.objects.count(), 2)
        self.assertEqual(models.User.objects.count(), 1)
