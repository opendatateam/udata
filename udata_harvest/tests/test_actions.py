# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from udata.tests import TestCase, DBTestMixin

from ..models import HarvestSource
from .factories import fake, HarvestSourceFactory
from .. import actions, signals

log = logging.getLogger(__name__)


class HarvestActionsTest(DBTestMixin, TestCase):
    def test_list_sources(self):
        self.assertEqual(actions.list_sources(), [])

        sources = [HarvestSourceFactory() for _ in range(3)]
        self.assertEqual(actions.list_sources(), sources)

    def test_create_source(self):
        source_url = fake.url()

        with self.assert_emit(signals.harvest_source_created):
            source = actions.create_source('Test source', source_url, 'dummy')

        self.assertEqual(source.name, 'Test source')
        self.assertEqual(source.slug, 'test-source')
        self.assertEqual(source.url, source_url)
        self.assertEqual(source.backend, 'dummy')
        self.assertEqual(source.jobs, [])
        self.assertEqual(source.frequency, 'manual')
        self.assertIsNone(source.owner)
        self.assertIsNone(source.organization)

    def test_get_source_by_slug(self):
        source = HarvestSourceFactory()
        self.assertEqual(actions.get_source(source.slug), source)

    def test_get_source_by_id(self):
        source = HarvestSourceFactory()
        self.assertEqual(actions.get_source(str(source.id)), source)

    def test_get_source_by_objectid(self):
        source = HarvestSourceFactory()
        self.assertEqual(actions.get_source(source.id), source)

    def test_delete_source_by_slug(self):
        source = HarvestSourceFactory()
        with self.assert_emit(signals.harvest_source_deleted):
            actions.delete_source(source.slug)
        self.assertEqual(len(HarvestSource.objects), 0)

    def test_delete_source_by_id(self):
        source = HarvestSourceFactory()
        with self.assert_emit(signals.harvest_source_deleted):
            actions.delete_source(str(source.id))
        self.assertEqual(len(HarvestSource.objects), 0)

    def test_delete_source_by_objectid(self):
        source = HarvestSourceFactory()
        with self.assert_emit(signals.harvest_source_deleted):
            actions.delete_source(source.id)
        self.assertEqual(len(HarvestSource.objects), 0)

    def test_launch(self):
        source = HarvestSourceFactory()
        with self.assert_emit(signals.harvest_job_started):
            actions.launch(source.id)
        source.reload()
        self.assertEqual(len(source.jobs), 1)

        job = source.jobs[0]


