# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from mock import patch

from udata.tests import TestCase, DBTestMixin

from ..tasks import purge_harvest_sources

log = logging.getLogger(__name__)


class HarvestActionsTest(DBTestMixin, TestCase):
    @patch('udata.harvest.actions.purge_sources')
    def test_purge(self, mock):
        '''It should purge from DB sources flagged as deleted'''
        purge_harvest_sources()
        mock.assert_called_once_with()
