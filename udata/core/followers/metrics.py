# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.core.metrics import Metric
from udata.i18n import lazy_gettext as _
from udata.models import Follow


__all__ = ('FollowersMetric', )


class FollowersMetric(Metric):
    name = 'followers'
    display_name = _('Followers')

    def get_value(self):
        return Follow.objects.followers(self.target).count()
