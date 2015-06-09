# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.core.metrics import Metric
from udata.i18n import lazy_gettext as _

from .models import Badge
from .signals import on_badge_added, on_badge_removed


class BadgesMetric(Metric):
    name = 'badges'
    display_name = _('Badges')

    def get_value(self):
        return Badge.objects(subject=self.target, removed=None).count()


@on_badge_added.connect
@on_badge_removed.connect
def update_badges_metric(badge, **kwargs):
    model = badge.subject.__class__
    for name, cls in Metric.get_for(model).items():
        if issubclass(cls, BadgesMetric):
            cls(target=badge.subject).trigger_update()
