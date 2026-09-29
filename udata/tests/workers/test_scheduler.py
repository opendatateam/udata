from datetime import datetime, timedelta

import pytest
from mongoengine.connection import get_db
from mongoengine.errors import ValidationError

from udata.core.jobs.models import PeriodicTask
from udata.core.jobs.scheduler import Scheduler
from udata.db.migrations import load_migration
from udata.tasks import celery
from udata.tests.api import PytestOnlyDBTestCase

MIGRATION = "2026-08-11-clean-periodic-task-legacy-fields.py"


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


class PeriodicTaskTest(PytestOnlyDBTestCase):
    def test_loads_a_document_carrying_the_legacy_cls(self):
        """Documents created before the model stopped inheriting still carry `_cls`."""
        task = PeriodicTask.objects.create(
            name="a legacy job",
            task="a-job",
            crontab=PeriodicTask.Crontab(minute="5"),
        )
        get_db().schedules.update_one(
            {"_id": task.id}, {"$set": {"_cls": "PeriodicTask.PeriodicTask"}}
        )

        assert PeriodicTask.objects.get(id=task.id).name == "a legacy job"

    def test_migration_makes_a_legacy_document_loadable(self):
        """A document written by `celerybeat-mongo` carries keys the strict model rejects."""
        migration = load_migration(MIGRATION)
        inserted = get_db().schedules.insert_one(
            {
                "name": "a legacy job",
                "task": "a-job",
                "enabled": True,
                "args": [],
                "kwargs": {},
                "_cls": "PeriodicTask.PeriodicTask",
                "crontab": {
                    "_cls": "Crontab.Crontab",
                    "minute": "5",
                    "hour": "*",
                    "day_of_week": "*",
                    "day_of_month": "*",
                    "month_of_year": "*",
                },
                **{key: "a value" for key in migration.LEGACY_FIELDS if "." not in key},
            }
        )

        migration.migrate(get_db())

        assert PeriodicTask.objects.get(id=inserted.inserted_id).crontab.minute == "5"
        assert Scheduler(app=celery).schedule["a legacy job"].schedule.minute == {5}

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
