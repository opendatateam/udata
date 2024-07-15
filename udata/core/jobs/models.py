from celerybeatmongo.models import PERIODS
from celerybeatmongo.models import PeriodicTask as BasePeriodicTask

from udata.i18n import lazy_gettext as _
from udata.mongo import db

__all__ = ("PeriodicTask", "PERIODS")

CRON = "{minute} {hour} {day_of_month} {month_of_year} {day_of_week}"


class PeriodicTask(BasePeriodicTask):
    last_run_id = db.StringField()

    class Interval(BasePeriodicTask.Interval):
        def __str__(self):
            if self.every == 1:
                return _("every {0.period_singular}").format(self)
            return _("every {0.every} {0.period}").format(self)

    class Crontab(BasePeriodicTask.Crontab):
        def __str__(self):
            return CRON.format(**self._data)

        @classmethod
        def parse(cls, cron):
            m, h, d, M, W = cron.split()
            return cls(
                minute=m,
                hour=h,
                day_of_month=d,
                month_of_year=M,
                day_of_week=W,
            )

    @property
    def schedule_display(self):
        if self.interval:
            return str(self.interval)
        elif self.crontab:
            return str(self.crontab)
        else:
            raise Exception("must define internal or crontab schedule")

    interval = db.EmbeddedDocumentField(Interval)
    crontab = db.EmbeddedDocumentField(Crontab)
