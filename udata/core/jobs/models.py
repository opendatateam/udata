# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from celerybeatmongo.models import PeriodicTask as BasePeriodicTask

from udata.models import db


__all__ = ('PeriodicTask', )


class PeriodicTask(BasePeriodicTask):
    last_id = db.StringField()
