# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import pytest

from udata.core.jobs.models import PeriodicTask
from udata.tasks import job

log = logging.getLogger(__name__)

JOB_NAME = 'fake-job'


@job(JOB_NAME)
def do_nothing(self, *args, **kwargs):
    log.info('Fake is running')


@pytest.fixture
def job_run(mocker):
    return mocker.patch.object(do_nothing, 'run')


@pytest.mark.usefixtures('clean_db')
class JobsCommandsTest:
    def test_list_jobs(self, cli):
        result = cli('job list')
        assert JOB_NAME in result.output

    def test_run_job(self, cli, job_run):
        cli('job run fake-job')
        job_run.assert_called()

    def test_delay_job(self, cli, job_run):
        cli('job run -d fake-job')
        job_run.assert_called()

    def test_run_job_kwargs(self, cli, job_run):
        cli('job run fake-job arg key=value')
        job_run.assert_called_with('arg', key='value')

    def test_schedule_job(self, cli):
        cli('job schedule fake-job "0 1 2 3 sunday"')

        tasks = PeriodicTask.objects(task=JOB_NAME)
        assert len(tasks) == 1

        task = tasks[0]
        assert task.args == []
        assert task.kwargs == {}
        assert task.crontab.minute == '0'
        assert task.crontab.hour == '1'
        assert task.crontab.day_of_month == '2'
        assert task.crontab.month_of_year == '3'
        assert task.crontab.day_of_week == 'sunday'
        assert task.enabled
        assert task.name == 'Job {0}'.format(JOB_NAME)

    def test_schedule_job_with_parameters(self, cli):
        cli('job schedule fake-job "0 1 2 3 sunday" '
            'arg0 arg1 key1=value1 key0=value0')

        tasks = PeriodicTask.objects(task=JOB_NAME)
        assert len(tasks) == 1

        task = tasks[0]
        assert task.args == ['arg0', 'arg1']  # Arguments order is preserved
        assert task.kwargs == {'key0': 'value0', 'key1': 'value1'}
        assert task.crontab.minute == '0'
        assert task.crontab.hour == '1'
        assert task.crontab.day_of_month == '2'
        assert task.crontab.month_of_year == '3'
        assert task.crontab.day_of_week == 'sunday'
        assert task.enabled
        # kwargs are sorted
        expected = 'Job {0}(arg0, arg1, key0=value0, key1=value1)'
        assert task.name == expected.format(JOB_NAME)
