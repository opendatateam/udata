# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.models import Activity


class ActivityView(object):
    max_activities = 15

    def get_context(self):
        context = super(ActivityView, self).get_context()

        qs = self.filter_activities(Activity.objects)
        context['activities'] = qs.order_by('-created_at').limit(self.max_activities)

        return context

    def filter_activities(self, qs):
        return qs
