"""The beat and the API share one collection, not one class.

`celery_mongobeat` reads and writes `schedules` straight through pymongo, while
`PeriodicTask` maps the very same collection with MongoEngine. Nothing in either
library enforces that the two agree, so these tests pin the contract down: the
documents we write must be readable by the beat, and the beat's writes must leave
our documents loadable.
"""

from datetime import datetime

import pytest
from celery_mongobeat.beat import MongoScheduler
from mongoengine.connection import get_db
from mongoengine.errors import ValidationError

from udata.core.jobs.models import PeriodicTask
from udata.db.migrations import load_migration
from udata.settings import Defaults
from udata.tasks import celery
from udata.tests.api import PytestOnlyDBTestCase

LEGACY_FIELDS = load_migration("2026-08-11-clean-periodic-task-legacy-fields.py").LEGACY_FIELDS

#: What the old stack stored for a crontab, minus the minute the tests set themselves.
CRONTAB_DEFAULTS = {
    "hour": "*",
    "day_of_week": "*",
    "day_of_month": "*",
    "month_of_year": "*",
}


def beat_entry_for(task: PeriodicTask):
    """The entry the beat builds out of a stored document.

    The scheduler is not instantiated: its `__init__` opens its own pymongo connection
    from `CELERY_MONGODB_SCHEDULER_URL`, which is derived before the test database name
    is applied. What matters here is the document reading itself, so we hand
    `_entry_from_document` the very document the beat's `find` would return.
    """
    scheduler = MongoScheduler.__new__(MongoScheduler)
    scheduler.app = celery
    return scheduler._entry_from_document(get_db().schedules.find_one({"_id": task.id}))


class PeriodicTaskBeatContractTest(PytestOnlyDBTestCase):
    def test_collection_is_the_one_the_beat_reads(self):
        assert PeriodicTask._meta["collection"] == Defaults.CELERY_MONGODB_SCHEDULER_COLLECTION

    def test_beat_reads_a_crontab_written_by_the_model(self):
        task = PeriodicTask.objects.create(
            name="a crontab job",
            task="a-job",
            enabled=True,
            args=["an-arg"],
            kwargs={"a-key": "a-value"},
            crontab=PeriodicTask.Crontab(minute="5", hour="2"),
        )

        entry = beat_entry_for(task)

        assert entry.name == "a crontab job"
        assert entry.task == "a-job"
        assert entry.args == ["an-arg"]
        assert entry.kwargs == {"a-key": "a-value"}
        assert entry.schedule.minute == {5}
        assert entry.schedule.hour == {2}

    def test_beat_reads_an_interval_written_by_the_model(self):
        task = PeriodicTask.objects.create(
            name="an interval job",
            task="a-job",
            enabled=True,
            interval=PeriodicTask.Interval(every=5, period="minutes"),
        )

        entry = beat_entry_for(task)

        assert entry.schedule.run_every.total_seconds() == 5 * 60

    def test_model_still_loads_after_the_beat_wrote_a_run(self):
        task = PeriodicTask.objects.create(
            name="a job that ran",
            task="a-job",
            enabled=True,
            crontab=PeriodicTask.Crontab(minute="5"),
        )

        # What `MongoScheduler.save_entry` writes after each run.
        last_run_at = datetime(2026, 8, 11, 9, 41)
        get_db().schedules.update_one(
            {"_id": task.id},
            {"$set": {"last_run_at": last_run_at, "total_run_count": 3, "run_immediately": False}},
        )

        task.reload()
        assert task.last_run_at == last_run_at
        assert task.total_run_count == 3
        assert task.crontab.minute == "5"

    def test_model_still_loads_a_document_carrying_the_legacy_cls(self):
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

    def test_migration_makes_a_legacy_document_usable_again(self):
        """A document written by the old stack carries keys the strict model rejects,
        and an embedded `_cls` the beat chokes on. The migration is what makes both work."""
        legacy = {
            "name": "a legacy job",
            "task": "a-job",
            "enabled": True,
            "args": [],
            "kwargs": {},
            "_cls": "PeriodicTask.PeriodicTask",
            "crontab": {"_cls": "Crontab.Crontab", **CRONTAB_DEFAULTS, "minute": "5"},
            **{key: "a value" for key in LEGACY_FIELDS if "." not in key},
        }
        inserted = get_db().schedules.insert_one(legacy)

        migration = load_migration("2026-08-11-clean-periodic-task-legacy-fields.py")
        migration.migrate(get_db())

        task = PeriodicTask.objects.get(id=inserted.inserted_id)
        assert task.crontab.minute == "5"
        assert beat_entry_for(task).schedule.minute == {5}

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
