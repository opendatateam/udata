from datetime import datetime, timedelta

import pytest
from bson import ObjectId
from mongoengine.connection import get_db
from mongoengine.errors import ValidationError

from udata.core.jobs.models import PeriodicTask
from udata.core.jobs.scheduler import Scheduler
from udata.db.migrations import load_migration
from udata.tasks import celery
from udata.tests.api import PytestOnlyDBTestCase

MIGRATION = "2026-08-11-clean-periodic-task-legacy-fields.py"

#: A crontab job as `celerybeat-mongo` 0.2.0 left it in production.
LEGACY_CRONTAB_JOB = {
    "_cls": "PeriodicTask",
    "name": "a legacy crontab job",
    "description": "A job written by the old stack",
    "task": "a-job",
    "enabled": True,
    "args": [],
    "kwargs": {},
    "crontab": {
        "_cls": "Crontab",
        "minute": "5",
        "hour": "*",
        "day_of_week": "*",
        "day_of_month": "*",
        "month_of_year": "*",
    },
    "last_run_at": datetime(2026, 8, 10, 9, 5),
    "last_run_id": "3aed026a-f8d2-4ecd-9fcf-79475512a39e",
    "max_run_count": 0,
    "total_run_count": 660,
    "run_immediately": False,
}

#: An interval job, the other schedule type, carrying its own embedded `_cls`.
LEGACY_INTERVAL_JOB = {
    "_cls": "PeriodicTask",
    "name": "a legacy interval job",
    "task": "a-job",
    "enabled": True,
    "args": [],
    "kwargs": {},
    "interval": {"_cls": "Interval", "every": 5, "period": "minutes"},
    "last_run_at": datetime(2026, 8, 10, 9, 5),
    "total_run_count": 3,
    "run_immediately": False,
}

#: What the old scheduler upserted after a job was deleted under it: run state only.
GHOST_JOB = {
    "total_run_count": 2775,
    "last_run_at": datetime(2019, 5, 20, 6, 46),
    "last_run_id": "3aed026a-f8d2-4ecd-9fcf-79475512a39e",
}


class SchedulerTest(PytestOnlyDBTestCase):
    def test_schedules_an_enabled_crontab_job(self):
        PeriodicTask.objects.create(
            name="a crontab job",
            task="a-job",
            enabled=True,
            args=["an-arg"],
            kwargs={"a-key": "a-value"},
            crontab=PeriodicTask.Crontab(minute="5", hour="2"),
        )

        entry = Scheduler(app=celery).schedule["a crontab job"]

        assert entry.task == "a-job"
        assert entry.args == ["an-arg"]
        assert entry.kwargs == {"a-key": "a-value"}
        assert entry.schedule.minute == {5}
        assert entry.schedule.hour == {2}

    def test_schedules_an_enabled_interval_job(self):
        PeriodicTask.objects.create(
            name="an interval job",
            task="a-job",
            enabled=True,
            interval=PeriodicTask.Interval(every=5, period="minutes"),
        )

        entry = Scheduler(app=celery).schedule["an interval job"]

        assert entry.schedule.run_every == timedelta(minutes=5)

    def test_ignores_a_disabled_job(self):
        PeriodicTask.objects.create(
            name="a disabled job",
            task="a-job",
            enabled=False,
            crontab=PeriodicTask.Crontab(minute="5"),
        )

        assert "a disabled job" not in Scheduler(app=celery).schedule

    def test_picks_up_a_job_created_after_startup_on_next_tick(self):
        scheduler = Scheduler(app=celery)
        # Ran a minute ago: not due, so the tick does not try to reach the broker.
        PeriodicTask.objects.create(
            name="a new job",
            task="a-job",
            enabled=True,
            interval=PeriodicTask.Interval(every=1, period="hours"),
            last_run_at=datetime.utcnow() - timedelta(minutes=1),
        )

        scheduler.tick()

        assert "a new job" in scheduler.schedule

    def test_a_sent_job_is_not_due_again_after_a_reload(self):
        task = PeriodicTask.objects.create(
            name="a due job",
            task="a-job",
            enabled=True,
            interval=PeriodicTask.Interval(every=5, period="minutes"),
            last_run_at=datetime.utcnow() - timedelta(minutes=10),
        )
        scheduler = Scheduler(app=celery)
        assert scheduler.schedule["a due job"].is_due().is_due

        scheduler.reserve(scheduler.schedule["a due job"])

        task.reload()
        assert task.last_run_at > datetime.utcnow() - timedelta(minutes=1)
        assert not Scheduler(app=celery).schedule["a due job"].is_due().is_due

    def test_a_job_that_never_ran_keeps_its_starting_point_across_restarts(self):
        task = PeriodicTask.objects.create(
            name="a new daily job",
            task="a-job",
            enabled=True,
            interval=PeriodicTask.Interval(every=1, period="days"),
        )

        first_start = Scheduler(app=celery).schedule["a new daily job"].last_run_at
        restart = Scheduler(app=celery).schedule["a new daily job"].last_run_at

        task.reload()
        assert task.last_run_at is not None
        assert restart == first_start


class PeriodicTaskMigrationTest(PytestOnlyDBTestCase):
    def test_makes_legacy_documents_schedulable(self):
        crontab_id = get_db().schedules.insert_one(dict(LEGACY_CRONTAB_JOB)).inserted_id
        interval_id = get_db().schedules.insert_one(dict(LEGACY_INTERVAL_JOB)).inserted_id

        load_migration(MIGRATION).migrate(get_db())

        crontab_job = PeriodicTask.objects.get(id=crontab_id)
        assert crontab_job.crontab.minute == "5"
        assert crontab_job.last_run_at == LEGACY_CRONTAB_JOB["last_run_at"]
        assert PeriodicTask.objects.get(id=interval_id).interval.every == 5
        schedule = Scheduler(app=celery).schedule
        assert schedule["a legacy crontab job"].schedule.minute == {5}
        assert schedule["a legacy interval job"].schedule.run_every == timedelta(minutes=5)

    def test_removes_keys_no_one_listed(self):
        """Any undeclared key goes, not only the ones seen on data.gouv.fr."""
        inserted = get_db().schedules.insert_one(
            {**LEGACY_CRONTAB_JOB, "foo": 1, "crontab": {**LEGACY_CRONTAB_JOB["crontab"], "bar": 1}}
        )

        load_migration(MIGRATION).migrate(get_db())

        document = get_db().schedules.find_one({"_id": inserted.inserted_id})
        assert "foo" not in document
        assert "bar" not in document["crontab"]
        assert PeriodicTask.objects.get(id=inserted.inserted_id).name == "a legacy crontab job"

    def test_deletes_documents_left_without_a_job(self):
        ghost_id = get_db().schedules.insert_one({"_id": ObjectId(), **GHOST_JOB}).inserted_id
        job_id = get_db().schedules.insert_one(dict(LEGACY_CRONTAB_JOB)).inserted_id

        load_migration(MIGRATION).migrate(get_db())

        assert get_db().schedules.find_one({"_id": ghost_id}) is None
        assert PeriodicTask.objects(id=job_id).count() == 1


class PeriodicTaskTest(PytestOnlyDBTestCase):
    def test_refuses_both_a_crontab_and_an_interval(self):
        with pytest.raises(ValidationError):
            PeriodicTask.objects.create(
                name="a mixed job",
                task="a-job",
                crontab=PeriodicTask.Crontab(minute="5"),
                interval=PeriodicTask.Interval(every=5, period="minutes"),
            )

    def test_refuses_neither_a_crontab_nor_an_interval(self):
        with pytest.raises(ValidationError):
            PeriodicTask.objects.create(name="a scheduleless job", task="a-job")
