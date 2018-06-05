# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import pytest

from ..tasks import purge_harvest_sources

log = logging.getLogger(__name__)


@pytest.mark.usefixtures('clean_db')
class HarvestActionsTest:
    def test_purge(self, mocker):
        '''It should purge from DB sources flagged as deleted'''
        mock = mocker.patch('udata.harvest.actions.purge_sources')
        purge_harvest_sources()
        mock.assert_called_once_with()
