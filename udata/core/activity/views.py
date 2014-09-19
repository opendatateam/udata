# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.frontend.views import DetailView
from udata.models import Activity
from udata.i18n import I18nBlueprint

blueprint = I18nBlueprint('activity', __name__)


class ActivityView(object):
    max_activities = 15

    def get_context(self):
        context = super(ActivityView, self).get_context()

        qs = self.filter_activities(Activity.objects)
        context['activities'] = qs.order_by('-created_at').limit(self.max_activities)

        return context

    def filter_activities(self, qs):
        return qs


class SiteActivityView(DetailView):
    template_name = 'site/activity.html'

    def get_context(self):
        context = super(SiteActivityView, self).get_context()
        context['activities'] = Activity.objects.order_by('-created_at')[:30]
        return context


blueprint.add_url_rule('/activity', view_func=SiteActivityView.as_view(str('activity')))
