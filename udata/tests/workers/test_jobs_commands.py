import logging

import pytest

from udata.core.jobs.commands import job_label
from udata.core.jobs.models import PeriodicTask
from udata.tasks import job

log = logging.getLogger(__name__)

JOB_NAME = "fake-job"


@job(JOB_NAME)
def do_nothing(self, *args, **kwargs):
    pass


@job("not-scheduled")
def not_scheduled(self):
    pass


@pytest.fixture
def job_run(mocker):
    return mocker.patch.object(do_nothing, "run")


@pytest.mark.usefixtures("clean_db")
class JobsCommandsTest:
    def test_list_jobs(self, cli):
        result = cli("job list")
        assert JOB_NAME in result.output

    def test_run_job(self, cli, job_run):
        cli("job run fake-job")
        job_run.assert_called()

    def test_delay_job(self, cli, job_run):
        cli("job run -d fake-job")
        job_run.assert_called()

    def test_run_job_kwargs(self, cli, job_run):
        cli("job run fake-job arg key=value")
        job_run.assert_called_with("arg", key="value")

    def test_schedule_job(self, cli):
        cli('job schedule "0 1 2 3 sunday" fake-job')

        tasks = PeriodicTask.objects(task=JOB_NAME)
        assert len(tasks) == 1

        task = tasks[0]
        assert task.args == []
        assert task.kwargs == {}
        assert task.crontab.minute == "0"
        assert task.crontab.hour == "1"
        assert task.crontab.day_of_month == "2"
        assert task.crontab.month_of_year == "3"
        assert task.crontab.day_of_week == "sunday"
        assert task.enabled
        assert task.name == "Job {0}".format(JOB_NAME)

    def test_schedule_job_with_parameters(self, cli):
        cli('job schedule "0 1 2 3 sunday" fake-job ' "arg0 arg1 key1=value1 key0=value0")

        tasks = PeriodicTask.objects(task=JOB_NAME)
        assert len(tasks) == 1

        task = tasks[0]
        assert task.args == ["arg0", "arg1"]  # Arguments order is preserved
        assert task.kwargs == {"key0": "value0", "key1": "value1"}
        assert task.crontab.minute == "0"
        assert task.crontab.hour == "1"
        assert task.crontab.day_of_month == "2"
        assert task.crontab.month_of_year == "3"
        assert task.crontab.day_of_week == "sunday"
        assert task.enabled
        # kwargs are sorted
        expected = "Job {0}(arg0, arg1, key0=value0, key1=value1)"
        assert task.name == expected.format(JOB_NAME)

    def test_scheduled_jobs(self, cli):
        tasks = [
            PeriodicTask.objects.create(
                task=JOB_NAME,
                name="job-1",
                description="I'm a scheduled job",
                enabled=True,
                crontab=PeriodicTask.Crontab.parse("0 0 0 0 0"),
            ),
            PeriodicTask.objects.create(
                task=JOB_NAME,
                name="job-2",
                description="I'm a scheduled job",
                enabled=True,
                args=["arg"],
                kwargs={"key": "value"},
                crontab=PeriodicTask.Crontab.parse("0 0 0 0 0"),
            ),
        ]
        result = cli("job scheduled")

        filtered = [line for line in result.output.splitlines() if "Tip" not in line]
        assert len(filtered) == len(tasks)

        assert "not-scheduled" not in result.output
        for task in tasks:
            label = job_label(task.task, task.args, task.kwargs)
            assert label in result.output
            assert task.name in result.output
            assert task.schedule_display in result.output

    def test_unschedule_job(self, cli):
        PeriodicTask.objects.create(
            task=JOB_NAME,
            name="job",
            description="I'm a scheduled job",
            enabled=True,
            crontab=PeriodicTask.Crontab.parse("0 0 0 0 0"),
        )
        cli("job unschedule {0}".format(JOB_NAME))

        assert len(PeriodicTask.objects(task=JOB_NAME)) == 0

    def test_unschedule_job_with_parameters(self, cli):
        PeriodicTask.objects.create(
            task=JOB_NAME,
            name="job",
            description="I'm a scheduled job",
            enabled=True,
            args=["arg"],
            kwargs={"key": "value"},
            crontab=PeriodicTask.Crontab.parse("0 0 0 0 0"),
        )
        cli("job unschedule {0} arg key=value".format(JOB_NAME))

        assert len(PeriodicTask.objects(task=JOB_NAME)) == 0

    def test_unschedule_job_different_parameters(self, cli):
        PeriodicTask.objects.create(
            task=JOB_NAME,
            name="job",
            description="I'm a scheduled job",
            enabled=True,
            crontab=PeriodicTask.Crontab.parse("0 0 0 0 0"),
        )
        result = cli("job unschedule {0} arg".format(JOB_NAME), check=False)

        assert result.exit_code != 0
        assert len(PeriodicTask.objects(task=JOB_NAME)) == 1

    def test_reschedule_job(self, cli):
        cli('job schedule "0 1 2 3 sunday" {0}'.format(JOB_NAME))
        cli('job schedule "1 0 0 0 *" {0}'.format(JOB_NAME))

        tasks = PeriodicTask.objects(task=JOB_NAME)
        assert len(tasks) == 1

        task = tasks[0]
        assert task.args == []
        assert task.kwargs == {}
        assert task.crontab.minute == "1"
        assert task.crontab.hour == "0"
        assert task.crontab.day_of_month == "0"
        assert task.crontab.month_of_year == "0"
        assert task.crontab.day_of_week == "*"
        assert task.enabled
        assert task.name == "Job {0}".format(JOB_NAME)
