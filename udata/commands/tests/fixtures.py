# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from udata.commands.fixtures import generate_fixtures
from udata import models

from udata.tests import TestCase, DBTestMixin


class FixturesTest(DBTestMixin, TestCase):

    def test_generate_fixtures_users(self):
        generate_fixtures()
        self.assertEqual(models.User.objects.count(), 2)
        user = models.User.objects(email='user@udata').first()
        admin = models.User.objects(email='admin@udata').first()
        self.assertFalse(user.has_role('admin'))
        self.assertTrue(admin.has_role('admin'))

    def test_generate_fixtures_datasets(self):
        generate_fixtures()
        self.assertEqual(models.Dataset.objects.count(), 10)
