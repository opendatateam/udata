# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from flask import url_for

from .. import actions

from udata.settings import Testing
from udata.tests.api import APITestCase


log = logging.getLogger(__name__)


class HarvestSettings(Testing):
    TEST_WITH_PLUGINS = True
    PLUGINS = ['harvest']


class HarvestAPITest(APITestCase):
    settings = HarvestSettings

    def test_list_backends(self):
        '''It should fetch the harvest backends list from the API'''
        response = self.get(url_for('api.harvest_backends'))
        self.assert200(response)
        self.assertEqual(len(response.json), len(actions.list_backends()))
        for data in response.json:
            self.assertIn('id', data)
            self.assertIn('label', data)
