# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.api import api
from udata.models import Dataset
from udata.tests import TestCase, DBTestMixin


class ModelResolutionTest(DBTestMixin, TestCase):
    def test_resolve_exact_match(self):
        self.assertEqual(api.resolve_model('Dataset'), Dataset)

    def test_resolve_from_dict(self):
        self.assertEqual(api.resolve_model({'class': 'Dataset'}), Dataset)

    def test_raise_if_not_found(self):
        with self.assertRaises(ValueError):
            api.resolve_model('NotFound')

    def test_raise_if_not_a_document(self):
        with self.assertRaises(ValueError):
            api.resolve_model('UDataMongoEngine')

    def test_raise_if_none(self):
        with self.assertRaises(ValueError):
            api.resolve_model(None)

    def test_raise_if_missing_class_entry(self):
        with self.assertRaises(ValueError):
            api.resolve_model({'field': 'value'})
