# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from celerybeatmongo.models import PeriodicTask as BasePeriodicTask, PERIODS

from udata.i18n import lazy_gettext as _
from udata.models import db


__all__ = ('PeriodicTask', 'PERIODS')


class PeriodicTask(BasePeriodicTask):
    last_run_id = db.StringField()

    class Interval(BasePeriodicTask.Interval):
        def __unicode__(self):
            if self.every == 1:
                return _('every {0.period_singular}').format(self)
            return _('every {0.every} {0.period}').format(self)

    @property
    def schedule_display(self):
        if self.interval:
            return str(self.interval)
        elif self.crontab:
            return str(self.crontab)
        else:
            raise Exception("must define internal or crontab schedule")
