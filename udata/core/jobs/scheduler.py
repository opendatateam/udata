from datetime import timedelta

from celery.beat import ScheduleEntry
from celery.beat import Scheduler as BaseScheduler
from celery.schedules import crontab, schedule

from udata.core.jobs.models import PeriodicTask


def celery_schedule(task: PeriodicTask) -> schedule:
    if task.interval:
        return schedule(timedelta(**{task.interval.period: task.interval.every}))
    return crontab(
        minute=task.crontab.minute,
        hour=task.crontab.hour,
        day_of_week=task.crontab.day_of_week,
        day_of_month=task.crontab.day_of_month,
        month_of_year=task.crontab.month_of_year,
    )


class Scheduler(BaseScheduler):
    """A Celery beat scheduler running the enabled `PeriodicTask`s.

    The schedule is reloaded on every tick, so that jobs created, edited or disabled
    through the API are picked up without restarting the beat.
    """

    def setup_schedule(self):
        # A job that never ran starts counting from its first load. Kept in memory only,
        # that starting point would move on every restart and on every edit of any job,
        # pushing back a long interval job for as long as those happen more often.
        PeriodicTask.objects(enabled=True, last_run_at=None).update(set__last_run_at=self.app.now())
        self.data = {
            task.name: ScheduleEntry(
                name=task.name,
                task=task.task,
                schedule=celery_schedule(task),
                args=task.args,
                kwargs=task.kwargs,
                last_run_at=task.last_run_at,
                app=self.app,
            )
            for task in PeriodicTask.objects(enabled=True)
        }

    def tick(self, *args, **kwargs):
        self.setup_schedule()
        return super().tick(*args, **kwargs)

    def reserve(self, entry):
        next_entry = super().reserve(entry)
        # Written as soon as the job is sent: the next tick reloads `last_run_at` from
        # the database, which must not see the job as still due.
        PeriodicTask.objects(name=entry.name).update(set__last_run_at=next_entry.last_run_at)
        return next_entry
