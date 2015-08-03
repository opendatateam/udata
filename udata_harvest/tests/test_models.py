# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from udata.models import Dataset, PeriodicTask

from udata.tests import TestCase, DBTestMixin
from udata.tests.factories import DatasetFactory, OrganizationFactory

from .factories import fake, HarvestSourceFactory, HarvestJobFactory
from ..models import HarvestSource, HarvestJob, HarvestError


log = logging.getLogger(__name__)


class HarvestSourceTest(DBTestMixin, TestCase):
    def test_defaults(self):
        source = HarvestSource.objects.create(name='Test', url=fake.url())
        self.assertEqual(source.name, 'Test')
        self.assertEqual(source.slug, 'test')

    def test_domain(self):
        source = HarvestSource(name='Test',
                               url='http://www.somewhere.com/path/')
        self.assertEqual(source.domain, 'www.somewhere.com')

        source = HarvestSource(name='Test',
                               url='https://www.somewhere.com/path/')
        self.assertEqual(source.domain, 'www.somewhere.com')

        source = HarvestSource(name='Test',
                               url='http://www.somewhere.com:666/path/')
        self.assertEqual(source.domain, 'www.somewhere.com')
