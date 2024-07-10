import logging

import pytest

from ..tasks import purge_harvest_jobs, purge_harvest_sources

log = logging.getLogger(__name__)


@pytest.mark.usefixtures("clean_db")
class HarvestActionsTest:
    def test_purge_sources(self, mocker):
        """It should purge from DB sources flagged as deleted"""
        mock = mocker.patch("udata.harvest.actions.purge_sources")
        purge_harvest_sources()
        mock.assert_called_once_with()

    def test_purge_jobs(self, mocker):
        """It should purge from DB jobs older than retention policy"""
        mock = mocker.patch("udata.harvest.actions.purge_jobs")
        purge_harvest_jobs()
        mock.assert_called_once_with()
