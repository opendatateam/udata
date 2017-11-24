# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.tests import TestCase
from udata.settings import Defaults
from udata.tasks import default_scheduler_config


class DefaultSchedulerConfigTest(TestCase):
    def test_parse_default_value(self):
        db, url = default_scheduler_config(Defaults.MONGODB_HOST)
        self.assertEqual(db, 'udata')
        self.assertEqual(url, 'mongodb://localhost:27017')

    def test_parse_url_with_auth(self):
        full_url = 'mongodb://userid:password@somewhere.com:1234/mydb'
        db, url = default_scheduler_config(full_url)
        self.assertEqual(db, 'mydb')
        self.assertEqual(url, 'mongodb://userid:password@somewhere.com:1234')

    def test_raise_exception_on_host_only(self):
        with self.assertRaises(ValueError):
            default_scheduler_config('somehost')

    def test_raise_exception_on_missing_db(self):
        with self.assertRaises(ValueError):
            default_scheduler_config('mongodb://somewhere.com:1234')
        with self.assertRaises(ValueError):
            default_scheduler_config('mongodb://somewhere.com:1234/')
